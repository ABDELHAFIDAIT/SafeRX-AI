import smtplib
import secrets
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.app.core.config import settings


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 3)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def send_credentials_email(
    to_email: str, first_name: str, role: str, plain_password: str
) -> None:
    # Traduction des rôles techniques en labels français
    role_labels = {
        "doctor": "Médecin",
        "pharmacist": "Pharmacien",
        "admin": "Administrateur",
    }
    role_label = role_labels.get(role, role.capitalize())

    subject = "SafeRx AI — Vos identifiants de connexion"

    # Template HTML moderne avec styles inline pour compatibilité maximale
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f8fafc; padding:32px;">
        <div style="max-width:520px; margin:auto; background:white; border-radius:16px;
                    padding:40px; box-shadow:0 4px 20px rgba(0,0,0,0.08); border:1px solid #e2e8f0;">

            <div style="text-align:center; margin-bottom:32px;">
                <div style="width:52px; height:52px; background:#2563eb; border-radius:14px;
                            display:inline-flex; align-items:center; justify-content:center; margin-bottom:12px;">
                    <span style="color:white; font-size:24px;">🔐</span>
                </div>
                <h2 style="color:#0f172a; margin:0; font-size:22px;">Bienvenue sur SafeRx AI</h2>
                <p style="color:#64748b; margin:6px 0 0; font-size:14px;">
                    Votre compte {role_label} a été créé
                </p>
            </div>

            <p style="color:#374151; font-size:15px;">
                Bonjour <strong>{first_name}</strong>,
            </p>
            <p style="color:#374151; font-size:14px; line-height:1.7;">
                Un compte vous a été créé sur la plateforme <strong>SafeRx AI</strong>.
                Voici vos identifiants de connexion :
            </p>

            <div style="background:#f1f5f9; border-radius:12px; padding:20px 24px; margin:24px 0;
                        border-left:4px solid #2563eb;">
                <p style="margin:0 0 10px; font-size:13px; color:#64748b; text-transform:uppercase;
                          letter-spacing:0.5px; font-weight:600;">Identifiants</p>
                <p style="margin:0 0 6px; font-size:14px; color:#1e293b;">
                    📧 <strong>Email :</strong> {to_email}
                </p>
                <p style="margin:0; font-size:14px; color:#1e293b;">
                    🔑 <strong>Mot de passe :</strong>
                    <code style="background:#e2e8f0; padding:2px 8px; border-radius:6px;
                                 font-size:14px; color:#1d4ed8;">{plain_password}</code>
                </p>
            </div>

            <div style="background:#fef9c3; border:1px solid #fde68a; border-radius:10px;
                        padding:14px 18px; margin-bottom:24px;">
                <p style="margin:0; font-size:13px; color:#92400e;">
                    ⚠️ <strong>Important :</strong> Veuillez changer votre mot de passe
                    dès votre première connexion.
                </p>
            </div>

            <p style="color:#64748b; font-size:13px; text-align:center; margin-top:32px;
                      border-top:1px solid #e2e8f0; padding-top:20px;">
                SafeRx AI · Clinical Decision Support System<br>
                Cet email a été envoyé automatiquement, merci de ne pas y répondre.
            </p>
        </div>
    </body>
    </html>
    """

    # Construit le message MIME multipart avec encodage HTML
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    # Connexion SMTP avec TLS optionnel et authentification conditionnelle
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
