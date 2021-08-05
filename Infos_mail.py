#Ce programme à pour objectif de repondre aux utilisateurs souhaitant récupérer les informations du magasin consommable 

# 1 Sur le mail mail_systeme@gmail.com il faut lire le dernier mail reçus
import imaplib
import email
from email.header import decode_header
import webbrowser
import os

from time import gmtime, strftime

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import smtplib
import configparser
from os.path import basename

import time

mail_systeme=''
mdp_systeme=''
default_address=''
###############################################################################################################
#-----------------------------------------------Variables-----------------------------------------------------#
###############################################################################################################
path_prog = "/home/pi/Documents/prog/"
config = configparser.ConfigParser()
config.read(path_prog + 'config.ini')
#recuperation des données du fichier config.ini
mail_magasinier = config.get('parametre',   'mail_magasinier')
nom_magasin = config.get('parametre',       'nom_magasin')
mail_systeme = config.get('parametre',      'mail_systeme')
default_address = config.get('parametre',   'mail_systeme')
mdp_systeme = config.get('parametre',       'mdp_systeme')
id_admin = config.get('parametre',          'id_admin')



# Ligne de dessous a decommenter si démarrage du programme sur l'ordinateur
#path_prog = ""

# Ligne de dessous a decommenter si démarrage du programme sur la raspberry 
path_prog = "/home/pi/Documents/prog/"

def Lire_mail():

        # create an IMAP4 class with SSL 
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(mail_systeme, mdp_systeme)

        status, messages = imap.select("INBOX")
        last_message= int(messages[0]) #nombre de mails
       
        res, msg = imap.fetch(str(last_message), "(RFC822)")
  
        for response in msg:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                from_ = msg.get("From")
                print("Subject:", subject)
                print("From:", from_)
                
                 #Verification de l'existance d'un fichier
                if subject=="? "+ nom_magasin :
                    if os.path.isfile(path_prog + 'materiel.xml'):
                        print("MAIL DEMANDANT INFO RECU")
                        send_mail(send_from= mail_systeme,
                            subject= "Informations Magasin "+ nom_magasin + strftime(" %d/%m/%y %H:%M"),
                            text="",
                            send_to= [from_,mail_systeme],
                            files = [path_prog + 'materiel.xml'])
                    else :  
                         print("MAIL DEMANDANT INFO RECU")
                         send_mail(send_from= mail_systeme,
                            subject= "Informations Magasin "+ nom_magasin + strftime(" %d/%m/%y %H:%M"),
                            text="",
                            send_to= [from_,mail_systeme],
                            files = [path_prog + 'outil.xml'])   
                    
        imap.close()
        imap.logout()

def send_mail(send_from: str, subject: str, text: str, send_to: list, files= None):
        global path_prog
        global mail_systeme
        global mdp_systeme
        #fonction d'envoi de mail avec PJ
        send_to = default_address  if not send_to else send_to
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

Lire_mail()
time.sleep(5)
print("fin_prog")
