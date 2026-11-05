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
    url = "https://www.universal-comics.com/comics.html"
    content = urllib.request.urlopen(url)
    dom = BeautifulSoup(content, "lxml")
    dom_comics = dom.find_all("div", class_="producto")
    lista_comics = []
    for comic in dom_comics:
        titulo = comic.find("h4", class_="titulo").a.string.strip()
        disponibilidad = comic.find(
            "span", class_="disponibilidad").string.strip()
        p_anterior = comic.find("span", class_="precio-anterior")
        if (p_anterior is None):
            p_original = float(comic.find("span", class_="precio").string.strip().split(" ")[
                0].replace(",", "."))
            p_descuento = p_original
        else:
            p_original = float(p_anterior.string.strip().split(" ")[
                0].replace(",", "."))
            p_descuento = float(comic.find("span", class_="precio").string.strip().split(" ")[
                0].replace(",", "."))
        indiv_url = comic.find("h4", class_="titulo").a['href']
        indiv_content = urllib.request.urlopen(
            "https://www.universal-comics.com"+indiv_url)
        indiv_dom = BeautifulSoup(indiv_content, "lxml")
        encuadernacion = indiv_dom.find("li", class_="encuadernacion").find(
            "span", class_="valor-propiedad").string.strip()
        fecha_edicion = indiv_dom.find("li", class_="fechaedicion").find(
            "span", class_="valor-propiedad").string.strip().split("/")
        fecha_edicion_def = fecha_edicion[2] + \
            "-"+fecha_edicion[1]+"-"+fecha_edicion[0]
        autor = indiv_dom.find("li", class_="autores").find(
            "span", class_="valor-propiedad").string.strip()
        coleccion = indiv_dom.find("li", class_="coleccion").find(
            "span", class_="valor-propiedad").string.strip()
        descuento = int(indiv_dom.find(
            "span", class_="descuento").string.strip()[:-1])
        lista_comics.append((titulo, disponibilidad, p_original, p_descuento,
                            encuadernacion, fecha_edicion_def, autor, coleccion, descuento))
    return lista_comics

def almacenar_datos():
    schem = Schema(titulo=TEXT(stored=True), disponibilidad=TEXT(stored=True), p_original=NUMERIC(stored=True), p_descuento=NUMERIC(stored=True), encuadernacion=TEXT(stored=True), fecha_edicion=DATETIME(stored=True), autor=TEXT(stored=True), coleccion=TEXT(stored=True), descuento=NUMERIC(stored=True))
    
    if os.path.exists("IndexComics"):
        shutil.rmtree("IndexComics")
    os.mkdir("IndexComics")
    
    #creamos el índice
    ix = create_in("IndexComics", schema=schem)
    writer = ix.writer()
    i=0
    lista=extraer_elementos()
    for j in lista:
        writer.add_document(titulo=j[0], disponibilidad=j[1], p_original=j[2], p_descuento=j[3], encuadernacion=j[4], fecha_edicion=datetime.strptime(j[5], "%Y-%m-%d"), autor=j[6], coleccion=j[7], descuento=j[8])
        i+=1
    writer.commit()
    messagebox.showinfo("Fin de indexado", "Se han indexado "+str(i)+ " comics")     
    
def listar_todos(cursor):
    v = Toplevel()
    v.title("ESTRENOS DE CINE")
    sc = Scrollbar(v)
    sc.pack(side=RIGHT, fill=Y)
    lb = Listbox(v, width = 150, yscrollcommand=sc.set)
    for row in cursor:
        lb.insert(END, "Título: "+row['titulo'])
        lb.insert(END, "\nDisponibilidad: "+row['disponibilidad'])
        lb.insert(END, "\nPrecio original: "+str(row['p_original']))
        lb.insert(END, "\nPrecio con descuento: "+str(row['p_descuento']))
        lb.insert(END, "\nEncuadernación: "+row['encuadernacion'])
        lb.insert(END, "\nFecha de edición: "+str(row['fecha_edicion']))
        lb.insert(END, "\nAutor: "+row['autor'])
        lb.insert(END, "\nColección: "+row['coleccion'])
        lb.insert(END, "\nDescuento: "+str(row['descuento'])+"%")
        lb.insert(END,"\n\n")
    lb.pack(side=LEFT,fill=BOTH)
    sc.config(command = lb.yview)
    
def ventana_principal():     
    def listar_todo():
        ix=open_dir("IndexComics")
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