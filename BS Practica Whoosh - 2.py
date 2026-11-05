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
    
    for p in range(1,5):
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
            
            poblacion = l1.find('div',class_='block-elto poblacion')
            if poblacion:
                poblacion = poblacion.find('div', class_='value').a.string.strip()
            else:
                poblacion = "Desconocido"
                
            fechas = l1.find('div', class_='block-elto fechas')
            if fechas:
                fechas = fechas.i.next_sibling.strip()
                fechas = re.findall('\d{2}/\d{2}/\d{4}', fechas)
                fecha_inicio = datetime.strptime(fechas[0], '%d/%m/%Y')
                if len(fechas) > 1:
                    fecha_fin = datetime.strptime(fechas[1], '%d/%m/%Y')
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

            lista.append((titulo,poblacion,fecha_inicio,fecha_fin,hora,categorias,descripcion))  

    return(lista)

def almacenar_datos():
    schem = Schema(título=TEXT(stored=True), población=KEYWORD(stored=True, commas=True), fecha_inicio=DATETIME(stored=True), fecha_fin=DATETIME(stored=True), hora=TEXT(stored=True), categorías=KEYWORD(stored=True), descripción=TEXT(stored=True), )
    
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
    
def imprimir_lista(cursor):
    
    v = Toplevel()
    v.title("EVENTOS DE SEVILLA")
    sc = Scrollbar(v)
    sc.pack(side=RIGHT, fill=Y)
    lb = Listbox(v, width = 150, yscrollcommand=sc.set)
    for row in cursor:
        lb.insert(END, "Título: "+row['título'])
        lb.insert(END, "Población: "+row['población'])
        lb.insert(END, "Fecha inicio: "+str(row['fecha_inicio']))
        lb.insert(END, "Fecha fin: "+str(row['fecha_fin']))
        lb.insert(END, "Hora: "+row['hora'])
        lb.insert(END, "Categorías: "+row['categorías'])
        lb.insert(END,"\n\n")
    lb.pack(side=LEFT,fill=BOTH)
    sc.config(command = lb.yview)   
    
def imprimir_lista_apartir_20h(cursor):
    v = Toplevel()
    v.title("ESTRENOS DE CINE A PARTIR DE LAS 20H")
    sc = Scrollbar(v)
    sc.pack(side=RIGHT, fill=Y)
    lb = Listbox(v, width = 150, yscrollcommand=sc.set)
    for row in cursor:
        if row['hora'] >= '20:00' and row['hora'] != 'Desconocido':
            lb.insert(END, "Título: "+row['título'])
            lb.insert(END, "Población: "+row['población'])
            lb.insert(END, "Fecha inicio: "+str(row['fecha_inicio']))
            lb.insert(END, "Fecha fin: "+str(row['fecha_fin']))
            lb.insert(END, "Hora: "+row['hora'])
            lb.insert(END, "Categorías: "+row['categorías'])
            lb.insert(END,"\n\n")
    lb.pack(side=LEFT,fill=BOTH)
    sc.config(command = lb.yview)
    
def buscar_categoria_y_titulo():
    def mostrar_lista():    
        with ix.searcher() as searcher:
            entrada = '"'+str(en.get())+'"' #se ponen comillas porque hay categorías con más de una palabra
            query = QueryParser("título", ix.schema).parse('categorías:' + entrada + ' NOT "' + str(en1.get()).strip() + '"')
            results = searcher.search(query,limit=3)
            imprimir_lista(results)
    
    v = Toplevel()
    v.title("Búsqueda por categorías y Título")
    l = Label(v, text="Seleccione categoría a buscar:")
    l.pack(side=LEFT)
    
    ix=open_dir("IndexSevilla")      
    with ix.searcher() as searcher:
        #lista de todas las categorias disponibles en el campo de caracteristicas
        lista_caracteristicas = [i.decode('utf-8') for i in searcher.lexicon('categorías')]
    
    en = Spinbox(v, values=lista_caracteristicas, state="readonly")
    en.pack(side=LEFT)
    
    l1 = Label(v, text="Escriba palabras que NO deben aparecer en el título:")
    l1.pack(side=LEFT)
    en1 = Entry(v, width=75)
    en1.pack(side=LEFT)
    
    b =Button(v, text="Buscar", command=mostrar_lista)
    b.pack(side=LEFT)
    
def buscar_15_titulo():
    def mostrar_lista(event):
            ix=open_dir("IndexSevilla")   
            with ix.searcher() as  searcher:
                query = QueryParser("título", ix.schema).parse('"'+ str(en.get()) + '"')
                results = searcher.search(query,limit=15)
                imprimir_lista(results)
        
    v = Toplevel()
    v.title("Búsqueda por Título")
            
    l1 = Label(v, text="Escriba el título:")
    l1.pack(side=LEFT)
    en = Entry(v, width=75)
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)
    
def buscar_poblacion():
    def mostrar_lista(event):    
        with ix.searcher() as searcher:
            entrada = '"'+str(en.get().strip())+'"'
            query = QueryParser("población", ix.schema).parse(entrada)
            results = searcher.search(query,limit=None)
            imprimir_lista(results)
    
    
    v = Toplevel()
    v.title("Búsqueda por Población")
    l = Label(v, text="Seleccione población a buscar:")
    l.pack(side=LEFT)
    
    ix=open_dir("IndexSevilla")      
    with ix.searcher() as searcher:
        #lista de todas las poblaciones
        lista_autores = [i.decode('utf-8') for i in searcher.lexicon('población')]
    
    en = Spinbox(v, values=lista_autores, state="readonly")
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)
    
def buscar_fecha_y_titulo():
    def mostrar_lista():
        ix = open_dir("IndexSevilla")   
        with ix.searcher() as searcher:
            fecha_str = str(en.get()).strip()
            s = re.compile('^\d{8}$').match(fecha_str)
            if s:
                # Evento activo en esa fecha: empieza antes o ese día ([TO fecha]) y termina ese día o después ([fecha TO])
                consulta = 'fecha_inicio:[TO ' + fecha_str + '] fecha_fin:[' + fecha_str + ' TO] ' + str(en1.get()).strip()
                query = QueryParser("título", ix.schema).parse(consulta)
                results = searcher.search(query, limit=None)
                imprimir_lista(results)
            else:
                messagebox.showerror("ERROR", "Formato de fecha incorrecto AAAAMMDD")
    
    v = Toplevel()
    v.title("Búsqueda por Fecha y Título")
    l = Label(v, text="Escriba una fecha (AAAAMMDD):")
    l.pack(side=LEFT)   
    en = Entry(v)
    en.pack(side=LEFT)
    
    l1 = Label(v, text="Escriba palabras del título:")
    l1.pack(side=LEFT)
    en1 = Entry(v, width=75)
    en1.pack(side=LEFT)
    
    b =Button(v, text="Buscar", command=mostrar_lista)
    b.pack(side=LEFT)
    
def ventana_principal():   
    def listar_todo():
        ix=open_dir("IndexSevilla")
        with ix.searcher() as searcher:
            results = searcher.search(query.Every(),limit=None)
            imprimir_lista(results)    
    def listar_noche():
            ix=open_dir("IndexSevilla")
            with ix.searcher() as searcher:
                results = searcher.search(query.Every(),limit=None)
                imprimir_lista_apartir_20h(results)   
    root = Tk()
    root.geometry("150x100")

    menubar = Menu(root)
    
    datosmenu = Menu(menubar, tearoff=0)
    datosmenu.add_command(label="Cargar", command=cargar)
    datosmenu.add_command(label="Listar", command=listar_todo)
    datosmenu.add_command(label="Listar a partir de las 20h", command=listar_noche)
    datosmenu.add_separator()   
    datosmenu.add_command(label="Salir", command=root.quit)

    menubar.add_cascade(label="Datos", menu=datosmenu)
    buscarmenu = Menu(menubar, tearoff=0)
    buscarmenu.add_command(label="Título", command=buscar_15_titulo)
    buscarmenu.add_command(label="Población", command=buscar_poblacion)
    buscarmenu.add_command(label="Categoria y Título", command=buscar_categoria_y_titulo)
    buscarmenu.add_command(label="Fecha y Título", command=buscar_fecha_y_titulo)
    menubar.add_cascade(label="Buscar", menu=buscarmenu)
        
    root.config(menu=menubar)
    root.mainloop()

    

if __name__ == "__main__":
    ventana_principal()