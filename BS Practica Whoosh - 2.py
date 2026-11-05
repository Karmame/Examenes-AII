from bs4 import BeautifulSoup
import urllib.request
from tkinter import *
from tkinter import messagebox
import re, os, shutil
from datetime import datetime
from whoosh import query
from whoosh.index import create_in,open_dir
from whoosh.fields import Schema, TEXT, DATETIME, KEYWORD, NUMERIC
from whoosh.qparser import MultifieldParser, QueryParser
from datetime import datetime

import os
import ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
        getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context
    
def cargar():
    respuesta = messagebox.askyesno(title="Confirmar",message="Esta seguro que quiere recargar los datos. \nEsta operación puede ser lenta")
    if respuesta:
        almacenar_datos()

def extraer_datos():
    lista=[]
    
    for p in range(1,4):
        req = urllib.request.Request("https://sevilla.cosasdecome.es/eventos/filtrar?pg="+str(p), headers={'User-Agent': 'Mozilla/5.0'})
        f = urllib.request.urlopen(req)
        s = BeautifulSoup(f, 'lxml')     
        
        l = s.find_all('div',class_='post-details')

        for i in l:
            titulo = i.a.string.strip()
                        
            req1 = urllib.request.Request(i.a['href'], headers={'User-Agent': 'Mozilla/5.0'})
            f1 = urllib.request.urlopen(req1)
            s1 = BeautifulSoup(f1, 'lxml')
            l1 = s1.find('section',class_='post-content')
            
            lugar = l1.find('div',class_='block-elto lugar')
            if lugar:
                lugar = "".join(lugar.find('div', class_='value').p.stripped_strings)
            else:
                lugar = "Desconocido"
            
            poblacion = l1.find('div',class_='block-elto poblacion')
            if poblacion:
                poblacion = poblacion.find('div', class_='value').a.string.strip()
            else:
                poblacion = "Desconocido"
                
            fechas = l1.find('div',class_='block-elto fechas')
            if fechas:
                fechas = fechas.i.next_sibling.strip()
                fechas = re.findall('\d{2}/\d{2}/\d{4}', fechas)
                fecha_inicio = fechas[0]
                if (len(fechas)>1):
                    fecha_fin = fechas[1]
                else:
                    fecha_fin = fecha_inicio
            else:
                fecha_inicio = None
                fecha_fin = None
                
            hora = l1.find('div',class_='block-elto hora')
            if hora:
                hora = list(hora.find('div', class_='value').strings)[1].strip()
            else:
                hora = "Desconocido"
                
            categorias = l1.find('div',class_='block-elto categoria')
            if categorias:
                cat = categorias.find_all('div', class_='value')
                categorias = cat[0].a.string.strip()
                for i in range(1,len(cat)):
                    categorias = categorias + ',' + cat[i].a.string.strip()
            else:
                categorias = "Desconocido"
                
            descripcion = l1.find('div',class_='block-elto descripcion')
            if descripcion:
                descripcion = descripcion.find('div', class_='value').text.strip()
            else:
                descripcion = "Desconocido"

            lista.append((titulo,lugar,poblacion,fecha_inicio,fecha_fin,hora,categorias,descripcion))  

    return(lista)

def almacenar_datos():
    schem = Schema(título=TEXT(stored=True), población=TEXT(stored=True), fecha_inicio=DATETIME(stored=True), fecha_fin=DATETIME(stored=True), hora=TEXT(stored=True), categorías=KEYWORD(stored=True), descripción=TEXT(stored=True))
    
    if os.path.exists("IndexSevilla"):
        shutil.rmtree("IndexSevilla")
    os.mkdir("IndexSevilla")
    
    #creamos el índice
    ix = create_in("IndexSevilla", schema=schem)
    writer = ix.writer()
    i=0
    lista=extraer_datos()
    for j in lista:
        writer.add_document(título=j[0], población=j[1], fecha_inicio=j[2], fecha_fin=j[3], hora=j[4], categorías=j[5], descripción=j[6])
        i+=1
    writer.commit()
    messagebox.showinfo("Fin de indexado", "Se han indexado "+str(i)+ " documentos")     
    
def ventana_principal():      
    root = Tk()
    root.geometry("150x100")

    menubar = Menu(root)
    
    datosmenu = Menu(menubar, tearoff=0)
    datosmenu.add_command(label="Cargar", command=cargar)
    datosmenu.add_separator()   
    datosmenu.add_command(label="Salir", command=root.quit)
    
    menubar.add_cascade(label="Datos", menu=datosmenu)
    buscarmenu = Menu(menubar, tearoff=0)
    
    menubar.add_cascade(label="Buscar", menu=buscarmenu)
        
    root.config(menu=menubar)
    root.mainloop()

    

if __name__ == "__main__":
    ventana_principal()