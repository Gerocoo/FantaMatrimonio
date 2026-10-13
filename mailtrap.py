import json
import urllib.request
import urllib.error


class Address:
    def __init__(self, email, name=None):
        self.email = email
        self.name = name

    def to_dict(self):
        d = {"email": self.email}
        if self.name:
            d["name"] = self.name
        return d


class Mail:
    def __init__(self, sender, to, subject, text=None, html=None, category=None, **kwargs):
        self.sender = sender
        self.to = to
        self.subject = subject
        self.text = text
        self.html = html
        self.category = category

    def to_dict(self):
        d = {
            "from": self.sender.to_dict(),
            "to": [a.to_dict() for a in self.to],
            "subject": self.subject,
        }
        if self.text:
            d["text"] = self.text
        if self.html:
            d["html"] = self.html
        if self.category:
            d["category"] = self.category
        return d


class MailtrapClient:
    def __init__(self, token, **kwargs):
        self.token = token

    def send(self, mail):
        req = urllib.request.Request(
            "https://send.api.mailtrap.io/api/send",
            data=json.dumps(mail.to_dict()).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + str(self.token),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "FantaMatrimonio/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:500]
            print("MAILTRAP HTTP", e.code, body, flush=True)
            raise