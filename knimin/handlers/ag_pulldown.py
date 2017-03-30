from tornado.web import authenticated
from future.utils import viewitems
from StringIO import StringIO
import pandas as pd

from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.lib.mem_zip import InMemoryZip
from knimin.handlers.access_decorators import set_access


@set_access(['Metadata Pulldown'])
class AGPulldownHandler(BaseHandler):
    @authenticated
    def get(self):
        surveys = db.list_external_surveys()
        self.render("ag_pulldown.html", currentuser=self.current_user,
                    barcodes=[], surveys=surveys, errors='',
                    agsurveys=db.list_ag_surveys(), merged='False')

    @authenticated
    def post(self):
        # Do nothing if no file given
        if 'barcodes' not in self.request.files:
            surveys = db.list_external_surveys()
            ags = db.list_ag_surveys(map(int, self.get_arguments('agsurveys')))
            self.render("ag_pulldown.html", currentuser=self.current_user,
                        barcodes='', blanks='', external='', surveys=surveys,
                        errors="No barcode file given, thus nothing could "
                               "be pulled down.", agsurveys=ags,
                        merged=self.get_argument('merged', default='False'))
            return
        # Get file information, ignoring commented out lines
        fileinfo = self.request.files['barcodes'][0]['body']
        lines = fileinfo.splitlines()
        # barcodes must be in first column, stripping in case extra spaces
        samples = [l.split('\t')[0].strip() for l in lines
                   if not l.startswith('#')]
        barcodes = [b for b in samples if not b.upper().startswith('BLANK')]
        blanks = [b for b in samples if b.upper().startswith('BLANK')]

        hold = self.get_arguments('external')

        if hold:
            external = ','.join(hold)
        else:
            external = ''
        surveys = db.list_external_surveys()
        ags = db.list_ag_surveys(map(int, self.get_arguments('agsurveys')))
        self.render("ag_pulldown.html", currentuser=self.current_user,
                    barcodes=",".join(barcodes), blanks=",".join(blanks),
                    surveys=surveys, external=external, errors='',
                    agsurveys=ags,
                    merged=self.get_argument('merged', default='False'))


@set_access(['Metadata Pulldown'])
class AGPulldownDLHandler(BaseHandler):
    @authenticated
    def post(self):
        barcodes = self.get_argument('barcodes').split(',')
        if self.get_argument('blanks'):
            blanks = self.get_argument('blanks').split(',')
        else:
            blanks = []

        # query which surveys have been selected by the user
        if self.get_argument('selected_ag_surveys', []):
            selected_ag_surveys = map(int, self.get_argument(
                'selected_ag_surveys').split(','))
        else:
            selected_ag_surveys = []

        if self.get_argument('external', []):
            external = self.get_argument('external').split(',')
        else:
            external = []

        # Get metadata and create zip file
        metadata, failures = db.pulldown(barcodes, blanks, external)

        meta_zip = InMemoryZip()
        failed = '\n'.join(['\t'.join(bc) for bc in viewitems(failures)])
        failtext = ("The following barcodes were not retrieved "
                    "for any survey:\n%s" % failed)
        meta_zip.append("failures.txt", failtext)

        # check database about what surveys are available
        available_agsurveys = {}
        for (id, name, selected) in db.list_ag_surveys():
            available_agsurveys[id] = name.replace(' ', '_')

        results_as_pd = []
        for survey, meta in viewitems(metadata):
            # only create files for those surveys that have been selected by
            # the user. Note that ids from the DB are negative, in metadata
            # they are positive!
            # Currently, I (Stefan Janssen) don't have test data for external
            # surveys, thus I don't know their 'survey' value. I expect it to
            # be the name of the external survey. In order to not block their
            # pulldown I check that a skipped survey ID must be in the set of
            # all available surveys.
            abs_survey = abs(survey)
            if (abs_survey in selected_ag_surveys) or \
               (abs_survey not in available_agsurveys):
                meta_zip.append('survey_%s_md.txt' %
                                available_agsurveys[-1 * survey], meta)
                # transform each survey into a pandas dataframe for later merge
                # read all columns as string to avoid unintened conversions,
                # like cutting leading zeros of barcodes
                pd_meta = pd.read_csv(StringIO(meta), sep="\t", dtype=str)
                # reset the index to barcodes = here sample_name
                pd_meta.set_index('sample_name', inplace=True)
                results_as_pd.append(pd_meta)

        # add the merged table of all selected surveys to the zip archive
        if self.get_argument('merged', default='False') == 'True':
            pd_all = pd.DataFrame()
            if len(results_as_pd) > 0:
                pd_all = pd.concat(results_as_pd, join='outer', axis=1)
                meta_zip.append('surveys_merged_md.txt',
                                pd_all.to_csv(sep='\t',
                                              index_label='sample_name'))

        # write out zip file
        self.add_header('Content-type',  'application/octet-stream')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition',
                        'attachment; filename=metadata.zip')
        self.write(meta_zip.write_to_buffer())
        self.flush()
        self.finish()


@set_access(['Metadata Pulldown'])
class UpdateEBIStatusHandler(BaseHandler):
    @authenticated
    def get(self):
        try:
            db.set_deposited_ebi()
            msg = 'Successfully updated barcodes in database'
        except Exception as e:
            msg = 'ERROR: %s' % str(e)
        self.write(msg)
