"""Send the daily summary + Excel attachment over SMTP."""
import os, smtplib, html
from datetime import date
from email.message import EmailMessage
import config


def _table(jobs, limit=25):
    if not jobs:
        return "<p>No new jobs today.</p>"
    rows = []
    for j in jobs[:limit]:
        rows.append(
            "<tr>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{html.escape(j.get('company',''))}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>"
            f"<a href='{html.escape(j.get('url',''))}'>{html.escape(j.get('title',''))}</a></td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{html.escape(j.get('location',''))}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{html.escape(j.get('experience',''))}</td>"
            "</tr>")
    more = f"<p style='color:#666'>+ {len(jobs)-limit} more in the attached Excel.</p>" if len(jobs) > limit else ""
    return ("<table style='border-collapse:collapse;font:14px system-ui,sans-serif'>"
            "<tr style='background:#1F3864;color:#fff'>"
            "<th style='padding:8px 10px;text-align:left'>Company</th>"
            "<th style='padding:8px 10px;text-align:left'>Role</th>"
            "<th style='padding:8px 10px;text-align:left'>Location</th>"
            "<th style='padding:8px 10px;text-align:left'>Experience</th></tr>"
            + "".join(rows) + "</table>" + more)


def send(new_jobs, attachment_path, stats):
    if not (config.SMTP_USER and config.SMTP_PASSWORD and config.EMAIL_TO):
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD / EMAIL_TO env vars not set")

    msg = EmailMessage()
    msg["Subject"] = config.EMAIL_SUBJECT.format(date=date.today().isoformat(), count=len(new_jobs))
    msg["From"] = config.EMAIL_FROM
    msg["To"] = ", ".join(config.EMAIL_TO)

    body = (f"<div style='font:14px system-ui,sans-serif'>"
            f"<h2 style='margin:0 0 4px'>{len(new_jobs)} new fresher software role(s)</h2>"
            f"<p style='color:#666;margin:0 0 16px'>"
            f"{stats['companies']} companies checked &middot; {stats['found']} matching jobs live &middot; "
            f"{stats['errors']} failed</p>"
            f"{_table(new_jobs)}</div>")
    msg.set_content(f"{len(new_jobs)} new fresher software roles. See attached Excel.")
    msg.add_alternative(body, subtype="html")

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            msg.add_attachment(f.read(),
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=os.path.basename(attachment_path))

    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)
    return True
