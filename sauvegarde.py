import os
import os.path
import tkinter as tk
import tkinter.font as tfFont
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import email
from email.header import decode_header
import webbrowser
from time import gmtime, strftime
import configparser
import re
from os.path import basename
import glob

path_prog = "/home/pi/Documents/prog/"

list_files = []

def send_mail( send_from: str, subject: str, text: str, send_to: list, files= None):
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
            attachedfile.add_header('content-disposition', 'attachment', filename=basename(f) )
        msg.attach(attachedfile)


    smtp = smtplib.SMTP("smtp.gmail.com", port= 587) 
    smtp.starttls()
    smtp.login(mail_systeme,mdp_systeme)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()
    
    
#ouverture du fichier de configuration
config = configparser.ConfigParser()
config.read(path_prog + 'config.ini')
#recuperation des données du fichier config.ini
mail_magasinier = config.get('parametre', 'mail_magasinier')
mail_systeme = config.get('parametre', 'mail_systeme')
nom_magasin = config.get('parametre', 'nom_magasin')
mdp_systeme = config.get('parametre', 'mdp_systeme')

#envoi d'un mail avec tout les fichiers en PJ
xml_files = glob.glob(path_prog + '*xml' )
ini_files = glob.glob(path_prog + '*ini' )
txt_files = glob.glob(path_prog + '*txt' )


for xml_files_i in xml_files:
    list_files.append(xml_files_i)
    
for ini_files_i in ini_files:
    list_files.append(ini_files_i)
    
for txt_files_i in txt_files:
    list_files.append(txt_files_i)


send_mail(send_from = mail_systeme,
subject= "Sauvegarde journalière " + nom_magasin +" du " + strftime("%d/%m/%y %H:%M"),
text="",
send_to= mail_magasinier ,
files= list_files)                  
