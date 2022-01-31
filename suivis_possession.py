import xml.etree.ElementTree as ET
import shutil
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart 
from email.mime.application import MIMEApplication
import configparser
import os
from os.path import basename


###############################################################################################################
#-----------------------------------------------Paramétrage des durées de possession--------------------------#
###############################################################################################################

rappel_emprunt = [15,30,45]
rappel_controle = [15,1]

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
    
    
if os.path.isfile(path_prog + 'outil.xml'):
###############################################################################################################
#-----------------------------------Declaration fonction------------------------------------------------------#
###############################################################################################################
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
            print("erreur mail.")
    ###############################################################################################################
    #-----------------------------------Debut du programme--------------------------------------------------------#
    ###############################################################################################################
    tree = ET.parse(path_prog +'outil.xml')
    root = tree.getroot()
    #alerte emprunt
    for child in root:

        #Recuperation de la date d expiration
        date_emprunt = child.find('date').text
        possesseur = child.find('possesseur').text

        date_emprunt=datetime.strptime(date_emprunt, '%d/%m/%y %H:%M')
        #recuyperation de la date actuelle
        date = datetime.now()
        #calcul de l ecart entre les 2 dates
        ecartSecondes=(date - date_emprunt).days
        print (ecartSecondes)
        #
        #Alerte 60 jours

        # Pour pemettre de rajouter des variables dans le tableau au debut du code sans avoir a toucher au reste
        for i_rappel in rappel_emprunt:
            if(i_rappel == ecartSecondes and possesseur != 'none'):
            #if((ecartSecondes == Rappel_n_un or ecartSecondes == Rappel_n_deux or ecartSecondes == Rappel_n_trois) and possesseur != 'none' ):

                #recuperation du mail du possesseur
                tree2 = ET.parse(path_prog +'personnel.xml')
                root2 = tree2.getroot()
                #boucle de controle
                for child2 in root2:
                    if(possesseur == child2.find('name').text):
                        mail_possesseur = child2.find('mail').text
                        print(mail_possesseur)
                #recuperation du nom de l'outil
                nom = child.find('nom').text
                identifiant = child.get('id')
                #Affichage du message dans la console
                #message = "Alerte "+ str(ecartSecondes) +" jours -  "+ str(nom)
                message = "Alerte "+nom_magasin +" "+ str(ecartSecondes) +" jours -  "+ str(identifiant) + " "+ nom + " - " + possesseur
                print(message)
                #envoi de l alerte par mail
                send_mail(send_from= mail_systeme,
                subject=message,
                text="",
                send_to= [mail_magasinier, mail_possesseur],
                files= [])


    #alerte expiration
    tree = ET.parse(path_prog +'outil.xml')
    root = tree.getroot()
    for child in root:

        #Recuperation de la date d expiration
        date_controle = child.find('date_controle').text
        possesseur = child.find('possesseur').text
        if possesseur == "":
            possesseur= "personne"
        date_controle = datetime.strptime(date_controle, '%d/%m/%Y')
        #recuyperation de la date actuelle
        date = datetime.now()
        #calcul de l ecart entre les 2 dates
        ecartSecondes=(date_controle - date).days
        ecartSecondes=ecartSecondes + 1 
        print (ecartSecondes)

        # Pour pemettre de rajouter des variables dans le tableau au debut du code sans avoir a toucher au reste
        for i_rappel in rappel_controle:
            if(i_rappel == ecartSecondes and possesseur != 'none' ):

                #recuperation du mail du possesseur
                tree2 = ET.parse(path_prog +'personnel.xml')
                root2 = tree2.getroot()
                #boucle de controle
                for child2 in root2:
                    if(possesseur == child2.find('name').text):
                        mail_possesseur = child2.find('mail').text
                        print(mail_possesseur)

                #recuperation du nom de l'outil
                nom = child.find('nom').text
                identifiant = child.get('id')
                #Affichage du message dans la console
                #message = "Alerte "+ str(ecartSecondes) +" jours -  "+ str(nom)
                message = "Alerte Controle "+nom_magasin +" "+ str(ecartSecondes) +" jours - Controle de l'outil "+ str(identifiant) + " " + nom + " - possédé par " + possesseur
                print(message)
                #envoi de l alerte par mail
                send_mail(send_from = mail_systeme,
                subject=message,
                text="",
                send_to= [mail_systeme],
                files= [])

