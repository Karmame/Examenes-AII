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
        
def extraer_elementos():
    url = "https://www.3djuegos.com/juegos/"
    f = urllib.request.urlopen(url) # descarga el HTML de la página 
    s = BeautifulSoup(f, "lxml") # convierte ese HTML en un árbol que BS puede recorrer 
    lista_juegos = []
    elementos = s.find("ul", class_="list_nov").find_all("li")

    for juego in elementos:
        
        plataformas = juego.find_all("span", class_="plats3")
        plataformas = ", ".join([i.string.strip() for i in plataformas])
        url = juego.a['href']
        f = urllib.request.urlopen(url)
        s = BeautifulSoup(f, "lxml")

        titulo = s.find("h1", class_=["s22"]).string.strip()
        desarrollador = s.find("dt", string=re.compile("Desarrollador:")).find_next_sibling("dd")
       
        if desarrollador.span:
            desarrollador = desarrollador.span.string.strip()
        else: 
            desarrollador = "desconocido"

        editor = s.find("dt", string="Editor:").find_next_sibling("dd")
        
        if editor.span:
            editor = editor.span.string.strip()
        else: 
            editor = "desconocido"
        

        genero = s.find("dt", class_="edit_tematicas").find_next_sibling("dd")
        
        if genero.a:
            genero = genero.a.string.strip()
        else: 
            genero = "desconocido"

        lanzamiento = s.find("dt", string="Lanzamiento:").find_next_sibling("dd")

        if lanzamiento.string:
            lanzamiento = lanzamiento.string.strip()
        else:
            lanzamiento = ""

        anos = re.findall(r"\d{4}", lanzamiento)

        if anos:
            ano = int(anos[0])
        else:
            ano = None
        lista_juegos.append((titulo, desarrollador, editor, genero, ano))
    return lista_juegos

def almacenar_datos():
    schem = Schema(titulo=TEXT(stored=True), desarrollador=TEXT(stored=True), editor=TEXT(stored=True), genero=TEXT(stored=True), ano=NUMERIC(stored=True))
    
    if os.path.exists("IndexJuegos"):
        shutil.rmtree("IndexJuegos")
    os.mkdir("IndexJuegos")
    
    #creamos el índice
    ix = create_in("IndexJuegos", schema=schem)
    writer = ix.writer()
    i=0
    lista=extraer_elementos()
    for j in lista:
        writer.add_document(titulo=j[0], desarrollador=j[1], editor=j[2], genero=j[3], ano=j[4])
        i+=1
    writer.commit()
    messagebox.showinfo("Fin de indexado", "Se han indexado "+str(i)+ " juegos")     
    
def listar_todos(cursor):
    v = Toplevel()
    v.title("ESTRENOS DE CINE")
    sc = Scrollbar(v)
    sc.pack(side=RIGHT, fill=Y)
    lb = Listbox(v, width = 150, yscrollcommand=sc.set)
    for row in cursor:
        lb.insert(END, "Titulo: "+row['titulo']+"\n")
        lb.insert(END, "Desarrollador: "+row['desarrollador']+"\n")
        lb.insert(END, "Editor: "+row['editor']+"\n")
        lb.insert(END, "Genero: "+row['genero']+"\n")
        lb.insert(END, "Año: "+str(row.get('ano', 'desconocido'))+"\n")
        lb.insert(END,"\n\n")
    lb.pack(side=LEFT,fill=BOTH)
    sc.config(command = lb.yview)
    
def ventana_principal():     
    def listar_todo():
        ix=open_dir("IndexJuegos")
        with ix.searcher() as searcher:
            results = searcher.search(query.Every(),limit=None)
            listar_todos(results)      
    root = Tk()
    root.geometry("150x100")

    menubar = Menu(root)
    
    datosmenu = Menu(menubar, tearoff=0)
    datosmenu.add_command(label="Cargar", command=cargar)
    datosmenu.add_command(label="Listar", command=listar_todo)
    datosmenu.add_separator()   
    datosmenu.add_command(label="Salir", command=root.quit)
    
    menubar.add_cascade(label="Datos", menu=datosmenu)
    
    buscarmenu = Menu(menubar, tearoff=0)
    
    menubar.add_cascade(label="Buscar", menu=buscarmenu)
        
    root.config(menu=menubar)
    root.mainloop()

    

if __name__ == "__main__":
    ventana_principal()