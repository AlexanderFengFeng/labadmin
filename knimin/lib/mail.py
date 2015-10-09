import errno
import smtplib
import socket

from email.mime.text import MIMEText

from knimin import config


def send_email(message, subject, recipient='americangut@gmail.com',
               sender=config.help_email, html=False):
    """Send an email from your local host"""

    msg = MIMEText(message, "html" if html else "plain")

    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    if config.smtp_ssl:
        s = smtplib.SMTP_SSL()
    else:
        s = smtplib.SMTP()

    try:
        s.connect(config.smtp_host, config.smtp_port)
    except socket.error as e:
        # TODO: Inability to connect to the mail server shouldn't prevent pages
        # from loading but it should be logged in some way
        if e.errno == errno.ECONNREFUSED:
            return
        else:
            raise

    # try tls, if not available on server just ignore error
    try:
        s.starttls()
    except smtplib.SMTPException:
        pass

    s.ehlo_or_helo_if_needed()

    if config.smtp_user:
        s.login(config.smtp_user, config.smtp_password)

    s.sendmail(sender, [recipient], msg.as_string())
    s.quit()
