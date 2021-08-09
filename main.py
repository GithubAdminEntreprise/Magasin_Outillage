# The code for changing pages was derived from: http://stackoverflow.com/questions/7546050/switch-between-two-frames-in-tkinter
# License: http://creativecommons.org/licenses/by-sa/3.0/   
import xml.etree.ElementTree as ET
import shutil
from shutil import copytree, ignore_patterns
import RPi.GPIO as GPIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart 
from email.mime.application import MIMEApplication
from os.path import basename

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import font
from tkinter.messagebox import showinfo
from time import gmtime, strftime

import imaplib
import email
from email.header import decode_header
import webbrowser
import os

import configparser

LARGE_FONT= ("Verdana", 15)
MEDIUM_FONT= ("Verdana", 10)

id_barcode = ''
id_user = ''
depot_list = []
retrait_list = []
id_page = ''
auth_level = ''
mail_user = []

mail_systeme = ''
mdp_systeme = ''
default_address = ''
mail_magasinier = ''
nom_magasin = ''
id_admin = ''

path_prog = "/home/pi/Documents/prog/"
duree_ouverture_gachette = 10*1000
reset_to_page_accueil = 5*60*1000

class SeaofBTCapp(tk.Tk):

    def __init__(self, *args, **kwargs):

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(3, GPIO.OUT)
        GPIO.output(3, GPIO.LOW)
        
        tk.Tk.__init__(self, *args, **kwargs)

        #INITIALISATION GENERAL
        #configuration de la fenetre
        self.geometry("800x480")
        self.attributes("-fullscreen", True)
        self.bind('<Key>', self.get_barcode)        
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for F in (StartPage, PageOne, PageTwo, PageAdmin, PageAjoutOutil, PageAjoutPersonnel, Magasinier, NomMagasin):

            frame = F(container, self)

            self.frames[F] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)
        
    def show_frame(self, cont):
        global id_page
        global id_barcode

        id_barcode = ''

        #Raz des textboxs à chaques fois 
        self.frames[Magasinier].nouveau_mail.delete(0,END)

        self.frames[PageAjoutPersonnel].entree_mail.delete(0,END)
        self.frames[PageAjoutPersonnel].entree_identifiant.delete(0,END)
        self.frames[PageAjoutPersonnel].entree_name.delete(0,END)

        self.frames[PageAjoutOutil].entree_id.delete(0,END)
        self.frames[PageAjoutOutil].entree_nom.delete(0,END)
        self.frames[PageAjoutOutil].entree_date_controle.delete(0,END)
        self.frames[PageAjoutOutil].entree_date_controle_expiration.delete(0,END)


        id_page=cont
        frame = self.frames[cont]
        frame.tkraise()

    def get_barcode(self, event):
        global id_barcode
        global object_list
        global id_user
        global auth_level
        global mail_user
        error = 0

        if event.keysym != 'Return':
            id_barcode += event.char

        elif event.keysym == 'Return':

            if id_barcode == id_admin:
                self.show_frame(PageAdmin)

            elif id_page == StartPage:
                
                #Traitement des données de la douchette laser pour la StartPage - Authentification utilisateur
                #recherche d'une correspondance code -> utilisateur dans le fichier personnel.xml
                tree = ET.parse(path_prog + 'personnel.xml')
                root = tree.getroot()
                for child in root:
                        id_bdd = child.get('id')
                        if id_bdd == id_barcode:
                            #on releve les informations de l'utilisateur (nom, auth, mail)
                            id_user = child.find('name').text
                            auth_level = child.find('auth').text
                            var =child.find('mail').text
                            mail_user.append(var)

                            #verrouillage/deverouillage des boutons en fonction du niveau d'autorisation de l'utilisateur
                            if auth_level == 'admin':
                                self.frames[PageOne].btn1['state'] = NORMAL
                            else:
                                self.frames[PageOne].btn1['state'] = DISABLED

                            #on affiche le nom de l'utilisateur
                            self.frames[PageOne].text.set('Nom: '+id_user)

                            #on reset le système au bout de 5 min
                            self.after(reset_to_page_accueil, self.reset)

                            #on verrouille la gache automatiquement au bout de 30sec
                            self.after(duree_ouverture_gachette, self.lock)

                            #On deverouille la gache
                            self.unlock()
                            
                            #on affiche la pageOne
                            self.show_frame(PageOne)

                            #Log des personnes entrant dans le magasin
                            fichier = open(path_prog + "log.txt", "a")
                            fichier.write("\nEntree  "+ strftime("%d/%m/%y %H:%M") + ":\t"+id_user+" est entree dans le magasin.")
                            fichier.close()
                id_barcode = ''
                            
                            
            elif id_page == PageOne:

                #Traitement des données de la douchette laser pour la PageOne - Depot/retrait
                #on regarde si l'outil retire n'a pas deja ete scanne
                for x in retrait_list:
                        if x == id_barcode:
                                error = 1
                #on regarde si l'outil depose n'a pas deja ete scanne
                for x in depot_list:
                        if x == id_barcode:
                                error = 1
                
                #si il n'y a pas d'erreur on affiche le nom de l'outil sur le GUI    
                if error == 0:
                        #recherche d'une correspondance code -> outil dans le fichier outil.xml
                        tree = ET.parse(path_prog + 'outil.xml')
                        root = tree.getroot()
                        for child in root:
                                id_bdd = child.get('id')
                                if id_bdd == id_barcode:
                                        name = child.find('nom').text
                                        owner = child.find('possesseur').text
                                        #si l'outil est marqué comme 'none' ou considere qu'il vient d'etre retire
                                        if owner == 'none':
                                                retrait_list.append(id_barcode)
                                                self.frames[PageOne].output_object.insert(END,name)
                                        else:
                                                #si le possesseur de l'outil est different de la personne qui vient de le scanner alors il y a une erreur
                                                if owner != id_user:
                                                    print("ERREUR:\tl'outil ' " + name + " ' est marqué comme emprunté par "+ owner +" mais c'est " + id_user + " qui vient de le scanner.")
                                                    fichier = open(path_prog + "log.txt", "a")
                                                    fichier.write("\nERREUR  "+ strftime("%d/%m/%y %H:%M") + ":\tl'outil ' " + name + " ' est marqué comme emprunté par "+ owner +" mais c'est " + id_user + " qui vient de le scanner.")
                                                    fichier.close()
                                                    retrait_list.append(id_barcode)
                                                    self.frames[PageOne].output_object.insert(END,name)
                                                    tree = ET.parse('outil.xml')
                                                    root = tree.getroot()
                                                    for child in root:
                                                            id_bdd = child.get('id')
                                                            if id_bdd == id_barcode:
                                                                    child.find('possesseur').text = 'none'
                                                    tree.write(path_prog + 'outil.xml')
                                                #aucun probleme, l'outil est marque comme depose dans le magasin                                                   
                                                else:
                                                    depot_list.append(id_barcode)
                                                    self.frames[PageOne].input_object.insert(END,name)
                        id_barcode = ''

            elif id_page == PageTwo:
                #Traitement des données de la douchette laser pour la PageTwo - informations outils
                tree = ET.parse(path_prog + 'outil.xml')
                root = tree.getroot()
                #on recherche les informations correspondants à l'outil et on les affiche
                for child in root:
                        id_bdd = child.get('id')
                        if id_bdd == id_barcode:
                                name = child.find('nom').text
                                owner = child.find('possesseur').text
                                date = child.find('date').text
                                self.frames[PageTwo].text.set('Outil: '+name)
                                self.frames[PageTwo].text2.set('possesseur: ' + owner)
                                self.frames[PageTwo].text3.set('date: ' + date)
                id_barcode = ''

    def reset(self):
            #reset universel, reinitialisation des variables globales et des pages, retour à la page d'acceuil
            global retrait_list
            global depot_list
            global id_user
            global mail_user
            global auth_level
            
            #raz des vars globales
            id_user = ''        
            code = ''
            auth_level = ''

            #raz des listes globales
            depot_list.clear()
            retrait_list.clear()
            mail_user.clear()  
            
            #reinitialisation des pages
            self.frames[PageTwo].text.set('Outil: ')
            self.frames[PageTwo].text2.set('possesseur: ')
            self.frames[PageTwo].text3.set('date: ')
            self.frames[PageOne].input_object.delete(0,END)        
            self.frames[PageOne].output_object.delete(0,END)

            #On verouille la gache
            self.lock()

            #retour a la page d'acceuil
            self.show_frame(StartPage)
    def lock(self):
        #verrouillage de la gache
        GPIO.output(3, GPIO.LOW)
        i=0

    def unlock(self):
        #deverrouillage de la gache
        GPIO.output(3, GPIO.HIGH)
        i=0
    def send_mail(self, send_from: str, subject: str, text: str, send_to: list, files= None):
        global path_prog
        #fonction d'envoi de mail avec PJ
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
        
class StartPage(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=4)
        self.rowconfigure(2, weight=1)
        
        #Text general
        self.label_nom_mag = tk.Label(self, text=nom_magasin+":", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')
        tk.Label(self, text="Veuillez scanner votre code barre personnel ... ", font=LARGE_FONT, justify = CENTER).grid(column = 0, row = 1, sticky='news')

        self.label1 = tk.Label(self, text="coucou", font=LARGE_FONT)
        self.label1.grid(column = 0, row = 2, sticky='news')

        #lancement de l'horloge
        self.update_clock(controller)

    def update_clock(self, controller):
        #affichage de l'heure sur la page d'acceuil
        now = strftime("%H:%M:%S")
        self.label1.configure(text=now)
        self.after(1000, lambda: self.update_clock(controller))

class PageOne(tk.Frame):
    #Constructeur de la page 1
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        #configuration ligne/colonne pageOne
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=2)
        self.rowconfigure(3, weight=1)
        
        #conteneur d'informations utilisateur
        labelframe_user = LabelFrame(self, text='Informations', font=LARGE_FONT)
        labelframe_user.grid(row=1, column=0,columnspan=2, sticky='news')

        #affichage du nom d'utilisateur
        self.text = tk.StringVar()        
        self.label_name=Label(labelframe_user, textvariable=self.text, font=MEDIUM_FONT)
        self.label_name.grid()

        #bouton menant à la pageTwo
        self.btn1 = Button(self, text ='admin',command=lambda: controller.show_frame(PageAdmin), font=LARGE_FONT, state = DISABLED)
        self.btn1.grid(row=1, column=2, sticky='news')

        self.btn2 = Button(self, text ='info?',command=lambda: controller.show_frame(PageTwo), font=LARGE_FONT, state = NORMAL)
        self.btn2.grid(row=1, column=3, sticky='news')

        #conteneur de la liste de retrait
        labelframe_output = LabelFrame(self, text="RETRAIT", font=LARGE_FONT)
        labelframe_output.grid(row=2, column=0,columnspan=2, sticky='news')

        #conteneur de la liste de depot
        labelframe_input = LabelFrame(self, text="DEPOT", font=LARGE_FONT)
        labelframe_input.grid(row=2, column=2,columnspan=2, sticky='news')

        #liste de retrait
        self.output_object = Listbox(labelframe_output, font=MEDIUM_FONT)
        self.output_object.pack(side=LEFT, fill='both', expand=1)

        #liste de depot
        self.input_object = Listbox(labelframe_input, font=MEDIUM_FONT)
        self.input_object.pack(side=LEFT, fill='both', expand=1)

        #bouton de validation
        Button(self, text ='Valider', bg = "green",command=lambda: self.validation(controller), font=LARGE_FONT).grid(row=3, column=2,columnspan=2, sticky='news')

        #bouton d'annulation
        Button(self, text ='Annuler', bg = "red",command=lambda: controller.reset(), font=LARGE_FONT).grid(row=3, column=0,columnspan=2, sticky='news')

    #Fonction de validation
    def validation(self,controller):        
        global object_list
        global path_prog
        global id_user

        #ouverture du fichier outil.xml
        tree = ET.parse(path_prog + 'outil.xml')
        root = tree.getroot()
        #enregistrement des outils retires
        for i in retrait_list:
                for child in root:
                        id_bdd = child.get('id')
                        if id_bdd == i:
                                name = child.find('nom').text
                                owner = child.find('possesseur').text
                                child.find('date').text = strftime("%d/%m/%y %H:%M", gmtime())
                                child.find('possesseur').text = id_user
                #log des outils retires
                fichier = open(path_prog + "log.txt", "a")
                fichier.write("\nRetrait "+ strftime("%d/%m/%y %H:%M") + ":\t" + id_user +" a retire l'outil: " + name + " /id: "+i+".")
                fichier.close()
        #enregistrement des outils deposes
        for i in depot_list:
                for child in root:
                        id_bdd = child.get('id')
                        if id_bdd == i:
                                name = child.find('nom').text
                                owner = child.find('possesseur').text
                                child.find('date').text = strftime("%d/%m/%y %H:%M", gmtime())
                                child.find('possesseur').text = "none"
                #log des outils deposes
                fichier = open("log.txt", "a")
                fichier.write("\nDepot   "+ strftime("%d/%m/%y %H:%M") + ":\t" + id_user +" a depose l'outil: " + name + " /id: "+i+".")
                fichier.close()
        tree.write(path_prog + 'outil.xml')

        #retour a la page d'acceuil
        controller.reset()

class PageTwo(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        #configuration ligne/colonne pageTwo
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)
        
        #Text general
        self.text = tk.StringVar()
        self.text.set("Veuillez scanner un outil pour obtenir son statut ...")
        tk.Label(self, textvariable=self.text, font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')

        #conteneur d'informations
        labelframe_status = LabelFrame(self, text='Informations')
        labelframe_status.grid(row=1, column=0, sticky='news')

        #affichage du possesseur
        self.text2 = tk.StringVar()
        self.text2.set("possesseur :")        
        self.label_name2=Label(labelframe_status, textvariable=self.text2, justify = LEFT, font=MEDIUM_FONT)
        self.label_name2.pack()
        #affichage de la derniere date
        self.text3 = tk.StringVar()
        self.text3.set("date :")        
        self.label_name3=Label(labelframe_status, textvariable=self.text3,justify = LEFT, font=MEDIUM_FONT)
        self.label_name3.pack()
        
        #bouton retour
        button1 = tk.Button(self, text="Retour",command=lambda: controller.show_frame(PageOne))
        button1.grid(row=2, column=0, sticky='news')

class PageAdmin(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        #configuration ligne/colonne pageTwo
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=0)
        self.rowconfigure(5, weight=1)
        
        #Text general
        self.text = tk.StringVar()
        self.text.set("Page d'administration")
        tk.Label(self, textvariable=self.text, font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0,columnspan=4, sticky='news')

        #conteneur d'informations
        #labelframe_status = LabelFrame(self, text='Informations')
        #labelframe_status.grid(row=1, column=0,columnspan=4, sticky='news')

        #bouton d'action
        button_copy = tk.Button(self, text="Ajout Outillage",command=lambda: controller.show_frame(PageAjoutOutil))
        button_copy.grid(row=1, column=0, sticky='news')

        button_copy = tk.Button(self, text="Ajout de Personnel",command=lambda: controller.show_frame(PageAjoutPersonnel))
        button_copy.grid(row=1, column=1, sticky='news')

        button_maj_personnel = tk.Button(self, text="MAJ Personnel",command=lambda: self.MAJ_PERSONNEL(controller))
        button_maj_personnel.grid(row=2, column=1, sticky='news')

        button_maj_materiel = tk.Button(self, text="MAJ Outillage",command=lambda: self.MAJ_OUTILLAGE(controller))
        button_maj_materiel.grid(row=2, column=2, sticky='news')

        button_maj_materiel = tk.Button(self, text="! MAJ CONFIG !",command=lambda: self.MAJ_CONFIG(controller))
        button_maj_materiel.grid(row=2, column=3, sticky='news')

        button_tr_mail = tk.Button(self, text="tr mail",command=lambda:  self.TRANSFERT_MAIL(controller))
        button_tr_mail.grid(row=2, column=0, sticky='news')

        button_reset = tk.Button(self, text="Reset Log",command=lambda:self.RESET_LOG())
        button_reset.grid(row=3, column=0, sticky='news')

        #bouton de sauvegarde des fichier dans le dossier backup
        button_sauvegarde = tk.Button(self, text="Sauvegarde",command=lambda: self.SAUVEGARDE())
        button_sauvegarde.grid(row=3, column=1, sticky='news')

        #bouton de restauration de la dernière sauvegarde
        button_restauration = tk.Button(self, text="Restauration",command=lambda: self.RESTAURATION())
        button_restauration.grid(row=3, column=2, sticky='news')

        #bouton mail du magasinier
        button_restauration = tk.Button(self, text="Magasinier",command=lambda: controller.show_frame(Magasinier))
        button_restauration.grid(row=3, column=3, sticky='news')

        #bouton nom du magaisn
        button_restauration = tk.Button(self, text="Nom Magasin",command=lambda: controller.show_frame(NomMagasin))
        button_restauration.grid(row=1, column=3, sticky='news')
                       
        
        #bouton retour
        button1 = tk.Button(self, text="Retour",command=lambda: controller.show_frame(PageOne))
        button1.grid(row=5, column=0,columnspan=4, sticky='news')

    def TRANSFERT_MAIL(self, controller):
        #envoi d'un mail avec tout les fichiers en PJ
        global mail_user
        global path_prog

        controller.send_mail(send_from= mail_systeme,
        subject= "Sauvegarde - " + nom_magasin + " - " + strftime("%d/%m/%y %H:%M"),
        text="",
        send_to= mail_systeme,
        files= [path_prog + 'outil.xml', path_prog + 'personnel.xml',path_prog +  'log.txt',path_prog +  'config.ini'])

    def RESET_LOG(self):
        global path_prog
        open(path_prog + 'log.txt', 'w').close()

    def MAJ_PERSONNEL(self, controller):
        global path_prog

        # create an IMAP4 class with SSL 
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(mail_systeme, mdp_systeme)

        status, messages = imap.select("INBOX")
        last_message= int(messages[0])

        res, msg = imap.fetch(str(last_message), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(path_prog, filename)
                                # download attachment and save it
                                if part.get_filename() ==  "personnel.xml":
                                    open(filepath, "wb").write(part.get_payload(decode=True))
        imap.close()
        imap.logout()

    def MAJ_OUTILLAGE(self, controller):
        global path_prog

        # create an IMAP4 class with SSL 
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(mail_systeme, mdp_systeme)

        status, messages = imap.select("INBOX")
        last_message= int(messages[0])

        res, msg = imap.fetch(str(last_message), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(path_prog, filename)
                                # download attachment and save it
                                if part.get_filename() == "outil.xml":
                                    open(filepath, "wb").write(part.get_payload(decode=True))
        imap.close()
        imap.logout()

    def MAJ_CONFIG(self, controller):
        global path_prog

        # create an IMAP4 class with SSL 
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(mail_systeme, mdp_systeme)

        status, messages = imap.select("INBOX")
        last_message= int(messages[0])

        res, msg = imap.fetch(str(last_message), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])   
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(path_prog, filename)
                                # download attachment and save it
                                if part.get_filename() == "config.ini":
                                    open(filepath, "wb").write(part.get_payload(decode=True))
        imap.close()
        imap.logout()
    
    def RESTAURATION(self):
        try:
            shutil.copy(path_prog + "backup/outil.xml",     path_prog + "outil.xml")
            shutil.copy(path_prog + "backup/personnel.xml", path_prog + "personnel.xml")
            shutil.copy(path_prog + "backup/config.ini",    path_prog +  "config.ini")
        except Exception as error:
            print(error)

    def SAUVEGARDE(self):
        if not os.path.isdir("backup/"):
            os.mkdir("backup/")

        shutil.copy(path_prog + "outil.xml",        path_prog + "backup/outil.xml")
        shutil.copy(path_prog + "personnel.xml",    path_prog + "backup/personnel.xml")
        shutil.copy(path_prog + "config.ini",       path_prog + "backup/config.ini")

class PageAjoutOutil(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)

        LabelFrame_textbox = LabelFrame(self)
        LabelFrame_textbox.grid(column=0,row=1, sticky='news')

        #configuration ligne/colonne StartPage
        LabelFrame_textbox.columnconfigure(0,   weight=1)
        LabelFrame_textbox.columnconfigure(1,   weight=3)
        LabelFrame_textbox.rowconfigure(0,      weight=1)
        LabelFrame_textbox.rowconfigure(1,      weight=1)
        LabelFrame_textbox.rowconfigure(2,      weight=1)
        LabelFrame_textbox.rowconfigure(3,      weight=1)
        LabelFrame_textbox.rowconfigure(4,      weight=1)
        
        #Label
        tk.Label(self, text="Ajout Outillage", font=LARGE_FONT, bg = 'green').grid(column = 0, row = 0, sticky='news', columnspan = 2)
        tk.Label(LabelFrame_textbox, text="ID*", font=LARGE_FONT).grid(column = 0, row = 0, sticky='e')
        tk.Label(LabelFrame_textbox, text="Nom*", font=LARGE_FONT).grid(column = 0, row = 1, sticky='e')
        tk.Label(LabelFrame_textbox, text="Date Controle", font=LARGE_FONT).grid(column = 0, row = 2, sticky='e')
        tk.Label(LabelFrame_textbox, text="Expiration", font=LARGE_FONT).grid(column = 0, row = 3, sticky='e')

        #textbox
        self.entree_id = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_id.grid(column = 1, row = 0, sticky='we')

        self.entree_nom = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_nom.grid(column = 1, row = 1, sticky='we')

        self.entree_date_controle = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_date_controle.grid(column = 1, row = 2, sticky='we')

        self.entree_date_controle_expiration = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_date_controle_expiration.grid(column = 1, row = 3, sticky='we')

        #labelframe pour les boutons
        LabelFrame_bouton = LabelFrame(self)
        LabelFrame_bouton.grid(column=0,row=2,columnspan=2, sticky='news')

        LabelFrame_bouton.columnconfigure(0, weight=1)
        LabelFrame_bouton.columnconfigure(1, weight=1)
        LabelFrame_bouton.rowconfigure(0, weight=1)

        #bouton d'annulation
        Button(LabelFrame_bouton, bg = "red", text='Annuler', font=LARGE_FONT,command=lambda: controller.show_frame(PageAdmin)).grid(column = 0, row = 0, sticky='news')        
        
        #bouton de validation
        Button(LabelFrame_bouton, bg = "green", text='Valider', font=LARGE_FONT,command=lambda: self.validation(controller)).grid(column = 1, row = 0, sticky='news')

    def validation(self,controller):
        global path_prog

        id_outillage = self.entree_id.get()
        nom_outillage = self.entree_nom.get()
        date_controle_outillage = self.entree_date_controle.get()
        date_controle_expiration_outillage = self.entree_date_controle_expiration.get()

        if date_controle_expiration_outillage == '':
                date_controle_expiration_outillage = "01/01/2099"
        if date_controle_outillage == '':
            date_controle_outillage = "01/01/1900"

        #On verifie que tous les champs sont completes
        if(id_outillage != '' and nom_outillage != ''):
            #remplissage du fichier materiel.xml
            tree = ET.parse(path_prog + 'outil.xml')
            
            a=tree.getroot()

            b = ET.SubElement(a, 'outil')        
            b.set('id', id_outillage)

            c1 = ET.SubElement(b, 'nom')
            c1.text = nom_outillage

            c2 = ET.SubElement(b, 'possesseur')
            c2.text = "none"

            c3 = ET.SubElement(b, 'date')
            c3.text = "0"

            c4 = ET.SubElement(b, 'date_controle')
            c4.text = date_controle_outillage

            c5 = ET.SubElement(b, 'date_controle_expiration')
            c5.text = date_controle_expiration_outillage
            
            tree2 = ET.ElementTree(a)
            tree2.write(path_prog + 'outil.xml')

            controller.show_frame(PageAdmin)
        else:
            #erreur, au moins un des champs doit être vide.
            print("erreur : au moins une des zones de texte est vide.")

class PageAjoutPersonnel(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)

        LabelFrame_textbox = LabelFrame(self)
        LabelFrame_textbox.grid(column=0,row=1, sticky='news')

        #configuration ligne/colonne StartPage
        LabelFrame_textbox.columnconfigure(0, weight=1)
        LabelFrame_textbox.columnconfigure(1, weight=3)
        LabelFrame_textbox.rowconfigure(0, weight=1)
        LabelFrame_textbox.rowconfigure(1, weight=1)
        LabelFrame_textbox.rowconfigure(2, weight=1)
        LabelFrame_textbox.rowconfigure(3, weight=1)
        LabelFrame_textbox.rowconfigure(4, weight=1)
        
        #Label
        tk.Label(self, text="Ajout de personnel*", font=LARGE_FONT, bg = 'green').grid(column = 0, row = 0, sticky='news', columnspan = 2)
        tk.Label(LabelFrame_textbox, text="Nom*", font=LARGE_FONT).grid(column = 0, row = 0, sticky='e')
        tk.Label(LabelFrame_textbox, text="Mail*", font=LARGE_FONT).grid(column = 0, row = 1, sticky='e')
        tk.Label(LabelFrame_textbox, text="Identifiant*", font=LARGE_FONT).grid(column = 0, row = 2, sticky='e')

        #textbox
        self.entree_name = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_name.grid(column = 1, row = 0, sticky='we')

        self.entree_mail = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_mail.grid(column = 1, row = 1, sticky='we')

        self.entree_identifiant = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_identifiant.grid(column = 1, row = 2, sticky='we')

        #labelframe pour les boutons
        LabelFrame_bouton = LabelFrame(self)
        LabelFrame_bouton.grid(column=0,row=2,columnspan=2, sticky='news')

        LabelFrame_bouton.columnconfigure(0, weight=1)
        LabelFrame_bouton.columnconfigure(1, weight=1)
        LabelFrame_bouton.rowconfigure(0, weight=1)

        #bouton d'annulation
        Button(LabelFrame_bouton, bg = "red", text='Annuler', font=LARGE_FONT,command=lambda: controller.show_frame(PageAdmin)).grid(column = 0, row = 0, sticky='news')        
        
        #bouton de validation
        Button(LabelFrame_bouton, bg = "green", text='Valider', font=LARGE_FONT,command=lambda: self.validation(controller)).grid(column = 1, row = 0, sticky='news')

    def validation(self,controller):
        global path_prog

        #On verifie que tous les champs sont completes
        if(self.entree_identifiant.get() != '' and self.entree_name.get() != '' and self.entree_mail.get() != ''):
            #remplissage du fichier materiel.xml
            tree = ET.parse(path_prog + 'personnel.xml')
            
            a=tree.getroot()

            b = ET.SubElement(a, 'personnel')        
            b.set('id', str(self.entree_identifiant.get()))

            c1 = ET.SubElement(b, 'name')
            c1.text = str(self.entree_name.get())

            c2 = ET.SubElement(b, 'auth')
            c2.text = "utilisateur"

            c3 = ET.SubElement(b, 'mail')
            c3.text = str(self.entree_mail.get())
            
            tree2 = ET.ElementTree(a)
            tree2.write(path_prog + 'personnel.xml')

            controller.show_frame(PageAdmin)
        else:
            #erreur, au moins un des champs doit être vide.
            print("erreur : au moins une des zones de texte est vide.")
class Magasinier(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=3)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        tk.Label(self, text="Masinier", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')
        tk.Label(self, text="Adresse mail du magasinier* ", font=LARGE_FONT, justify = CENTER).grid(column = 0, row = 1, sticky='news')        

        self.nouveau_mail = ttk.Entry(self, width = 15, font=LARGE_FONT)
        self.nouveau_mail.grid(column = 0, row = 2, sticky='we')

        self.btn1 = Button(self, state = NORMAL, text="Valider ", font=LARGE_FONT, width=0, height=0,background="green",command=lambda: self.validation(controller))
        self.btn1.grid(row=3, column=0, sticky='news')

        self.btn1 = Button(self, state = NORMAL, text="Retour", font=LARGE_FONT, width=0, height=0, background="red",command=lambda: controller.show_frame(PageAdmin))
        self.btn1.grid(row=4, column=0, sticky='news')

    def validation(self,controller):
        #ici on modifira l'adresse mail du magasinier
        global mail_magasinier
        global id_barcode
        global path_prog

        mail_magasinier = self.nouveau_mail.get()

        config = configparser.ConfigParser()
        config.read(path_prog + 'config.ini')        
        config.set('parametre', 'mail_magasinier', mail_magasinier)

        with open(path_prog + 'config.ini', 'w') as configfile:
            config.write(configfile)

        controller.reset()
class NomMagasin(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=3)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        tk.Label(self, text="Nom du Magasin", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')
        tk.Label(self, text="Nouveau nom du magasin* ", font=LARGE_FONT, justify = CENTER).grid(column = 0, row = 1, sticky='news')        

        self.nouveau_nom_magasin = ttk.Entry(self, width = 15, font=LARGE_FONT)
        self.nouveau_nom_magasin.grid(column = 0, row = 2, sticky='we')

        self.btn1 = Button(self, state = NORMAL, text="Valider ", font=LARGE_FONT, width=0, height=0,background="green",command=lambda: self.validation(controller))
        self.btn1.grid(row=3, column=0, sticky='news')

        self.btn1 = Button(self, state = NORMAL, text="Retour", font=LARGE_FONT, width=0, height=0, background="red",command=lambda: controller.show_frame(PageAdmin))
        self.btn1.grid(row=4, column=0, sticky='news')

    def validation(self,controller):
        #ici on modifira le nom du magasin
        global nom_magasin
        global path_prog

        nom_magasin = self.nouveau_nom_magasin.get()

        config = configparser.ConfigParser()
        config.read(path_prog + 'config.ini')        
        config.set('parametre', 'nom_magasin', nom_magasin)

        with open(path_prog + 'config.ini', 'w') as configfile:
            config.write(configfile)

        controller.reset()


#ouverture du fichier de configuration
config = configparser.ConfigParser()
config.read(path_prog + 'config.ini')

#recuperation des données du fichier config.ini
mail_magasinier = config.get('parametre',   'mail_magasinier')
nom_magasin = config.get('parametre',       'nom_magasin')
mail_systeme = config.get('parametre',      'mail_systeme')
default_address = config.get('parametre',   'mail_systeme')
mdp_systeme = config.get('parametre',       'mdp_systeme')
id_admin = config.get('parametre',          'id_admin')

app = SeaofBTCapp()
app.mainloop()
