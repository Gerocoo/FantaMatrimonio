import smtplib

smtp_server = "smtp.ionos.it"
port = 587  # usa 465 se preferisci SSL
sender_email = "register@therealfantamatrimonio.it"
password = "Aeiou123aeiou@@!suca"

try:
    server = smtplib.SMTP(smtp_server, port, timeout=10)
    server.starttls()
    server.login(sender_email, password)
    print("Login SMTP riuscito!")
    # Prova a inviare un'email a te stesso come test
    server.sendmail(sender_email, sender_email, "Subject: Test invio email\n\nQuesta è una mail di test.")
    print("Email di test inviata con successo!")
except Exception as e:
    print(f"Errore SMTP: {e}")
finally:
    server.quit()
