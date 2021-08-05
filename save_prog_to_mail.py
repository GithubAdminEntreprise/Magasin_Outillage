import xml.etree.ElementTree as ET
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from os.path import basename
from time import gmtime, strftime
import imaplib
import email
from email.header import decode_header
import webbrowser
import os
import configparser
import glob

def send_mail(send_from: str, subject: str, text: str, send_to: list, files= None):
        try:
            send_to= default_address if not send_to else send_to

            msg = MIMEMultipart()
            msg['From'] = send_from
            msg['To'] = ', '.join(send_to)  
            msg['Subject'] = subject

            msg.attach(MIMEText(text))

            for f in files or []:
                with open(f, "rb") as fil: 
                    ext = f.split('.')[-1:]
                    attachedfile = MIMEApplication(fil.read(), _subtype = ext)
                    attachedfile.add_header(
                        'content-disposition', 'attachment', filename=basename(f) )
                msg.attach(attachedfile)


            smtp = smtplib.SMTP("smtp.gmail.com", port= 587) 
            smtp.starttls()
            smtp.login(mail_systeme,mdp_systeme)
            smtp.sendmail(send_from, send_to, msg.as_string())
            smtp.close()
        except:
            showerror(title="Erreur de saisie", message= "saisie invalide.")

path_prog = "/home/pi/Documents/prog/"

#ouverture du fichier de configuration
config = configparser.ConfigParser()
config.read(path_prog + 'config.ini')

#recuperation des données du fichier config.ini
mail_magasinier = config.get('parametre', 'mail_magasinier')
nom_magasin = config.get('parametre',       'nom_magasin')
mail_systeme = config.get('parametre', 'mail_systeme')
default_address = config.get('parametre', 'mail_systeme')
mdp_systeme = config.get('parametre', 'mdp_systeme')
id_admin = config.get('parametre', 'id_admin')

py_files = glob.glob(path_prog + '*py' )
    
send_mail(send_from= mail_systeme,
        subject= "Savegarde des programmes " + nom_magasin +" du " + strftime("%d/%m/%y %H:%M"),
        text="",
        send_to= mail_systeme,
        files= py_files)


