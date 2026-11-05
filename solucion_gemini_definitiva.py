import urllib.request
from bs4 import BeautifulSoup
import re
import os
import shutil
from datetime import datetime
from tkinter import *
from tkinter import messagebox

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, DATETIME, KEYWORD
from whoosh.qparser import QueryParser
from whoosh import qparser, query, index
from whoosh import scoring

import ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context

def extraer_datos():
    lista = []
    for p in range(1, 5):
        req = urllib.request.Request("https://sevilla.cosasdecome.es/eventos/filtrar?pg="+str(p), headers={'User-Agent': 'Mozilla/5.0'})
        f = urllib.request.urlopen(req)
        s = BeautifulSoup(f, 'lxml')     
        l = s.find_all('div', class_='post-details')

        for i in l:
            titulo = i.a.string.strip()
                        
            req1 = urllib.request.Request(i.a['href'], headers={'User-Agent': 'Mozilla/5.0'})
            f1 = urllib.request.urlopen(req1)
            s1 = BeautifulSoup(f1, 'lxml')
            l1 = s1.find('section', class_='post-content')
            
            poblacion = l1.find('div', class_='block-elto poblacion')
            poblacion = poblacion.find('div', class_='value').a.string.strip() if poblacion else "Desconocido"
                
            fechas = l1.find('div', class_='block-elto fechas')
            if fechas:
                fechas_texto = fechas.i.next_sibling.strip()
                fechas_lista = re.findall(r'\d{2}/\d{2}/\d{4}', fechas_texto)
                fecha_inicio = fechas_lista[0] if fechas_lista else None
                fecha_fin = fechas_lista[1] if len(fechas_lista) > 1 else fecha_inicio
            else:
                fecha_inicio = None
                fecha_fin = None
                
            hora = l1.find('div', class_='block-elto hora')
            hora = list(hora.find('div', class_='value').strings)[1].strip() if hora else "Desconocido"
                
            categorias_tag = l1.find('div', class_='block-elto categoria')
            if categorias_tag:
                cat = categorias_tag.find_all('div', class_='value')
                categorias = ",".join([c.a.string.strip() for c in cat if c.a])
            else:
                categorias = "Desconocido"
                
            descripcion = l1.find('div', class_='block-elto descripcion')
            descripcion = descripcion.find('div', class_='value').text.strip() if descripcion else "Desconocido"

            lista.append((titulo, poblacion, fecha_inicio, fecha_fin, hora, categorias, descripcion))  
    return lista


def cargar():
    if index.exists_in("IndexEventos"):
        respuesta = messagebox.askyesno(title="Confirmar", message="EL ÍNDICE YA EXISTE.\n¿Está seguro de que quiere volver a crearlo?\nEsta operación puede ser lenta.")
        if respuesta:
            almacenar_datos()
    else:
        almacenar_datos()

def almacenar_datos():
    schem = Schema(
        titulo=TEXT(stored=True, phrase=False),
        poblacion=KEYWORD(stored=True, commas=True),
        fecha_inicio=DATETIME(stored=True),
        fecha_fin=DATETIME(stored=True),
        hora=TEXT(stored=True),
        categorias=KEYWORD(stored=True, commas=True),
        descripcion=TEXT(stored=True)
    )

    if os.path.exists("IndexEventos"):
        shutil.rmtree("IndexEventos")
    os.mkdir("IndexEventos")

    ix = create_in("IndexEventos", schema=schem)
    writer = ix.writer()
    i = 0
    lista = extraer_datos()
    for ev in lista:
        t, p, f_ini, f_fin, h, c, d = ev
        dt_ini = datetime.strptime(f_ini, "%d/%m/%Y") if f_ini else None
        dt_fin = datetime.strptime(f_fin, "%d/%m/%Y") if f_fin else None

        writer.add_document(
            titulo=str(t),
            poblacion=str(p),
            fecha_inicio=dt_ini,
            fecha_fin=dt_fin,
            hora=str(h),
            categorias=str(c),
            descripcion=str(d)
        )    
        i += 1
    writer.commit()
    messagebox.showinfo("Fin de indexado", f"Se han indexado {i} eventos")

def imprimir_lista(cursor):
    v = Toplevel()
    v.title("EVENTOS GASTRONÓMICOS")
    sc = Scrollbar(v)
    sc.pack(side=RIGHT, fill=Y)
    lb = Listbox(v, width=150, yscrollcommand=sc.set)
    for row in cursor:
        lb.insert(END, row['titulo'])
        lb.insert(END, "    Población: " + row['poblacion'])
        
        f_ini = datetime.strftime(row['fecha_inicio'], "%d/%m/%Y") if row.get('fecha_inicio') else "Sin fecha"
        f_fin = datetime.strftime(row['fecha_fin'], "%d/%m/%Y") if row.get('fecha_fin') else "Sin fecha"
        
        if f_ini == f_fin:
            lb.insert(END, "    Fecha: " + f_ini)
        else:
            lb.insert(END, "    Fecha Inicio: " + f_ini + " - Fecha Fin: " + f_fin)
            
        lb.insert(END, "    Hora: " + row['hora'])
        lb.insert(END, "    Categoría/s: " + row['categorias'])
        lb.insert(END, "---------------------------------------------------------------------------------------------------------------")
    lb.pack(side=LEFT, fill=BOTH)
    sc.config(command=lb.yview)

def listar_todos():
    ix = open_dir("IndexEventos")
    with ix.searcher() as searcher:
        results = searcher.search(query.Every(), limit=None)
        imprimir_lista(results)

def listar_noche():
    ix = open_dir("IndexEventos")
    with ix.searcher() as searcher:
        results = searcher.search(query.Every(), limit=None)
        eventos_noche = []
        for row in results:
            match = re.search(r'(\d{1,2}):(\d{2})', row['hora'])
            if match:
                h = int(match.group(1))
                if h >= 20:
                    eventos_noche.append(row)
        imprimir_lista(eventos_noche)

def buscar_titulo():
    def mostrar_lista(event=None):
        ix = open_dir("IndexEventos")
        with ix.searcher() as searcher:
            qp = QueryParser("titulo", ix.schema, group=qparser.OrGroup)
            q = qp.parse(str(en.get()))
            results = searcher.search(q, limit=15)
            imprimir_lista(results)

    v = Toplevel()
    v.title("Búsqueda por Título")
    l = Label(v, text="Introduzca palabra(s) del título:")
    l.pack(side=LEFT)
    en = Entry(v, width=50)
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)

def buscar_poblacion():
    def mostrar_lista(event=None):
        ix = open_dir("IndexEventos")
        with ix.searcher() as searcher:
            entrada = '"' + str(spin.get().strip()) + '"'
            q = QueryParser("poblacion", ix.schema).parse(entrada)
            results = searcher.search(q, limit=None)
            imprimir_lista(results)

    v = Toplevel()
    v.title("Eventos por Población")
    l = Label(v, text="Seleccione población:")
    l.pack(side=LEFT)

    ix = open_dir("IndexEventos")      
    with ix.searcher() as searcher:
        lista_poblaciones = [i.decode('utf-8') for i in searcher.lexicon('poblacion')]

    spin = Spinbox(v, values=lista_poblaciones, state="readonly")
    spin.bind("<Return>", mostrar_lista)
    spin.pack(side=LEFT)
    
    b = Button(v, text="Buscar", command=mostrar_lista)
    b.pack(side=LEFT)

def buscar_categoria_titulo():
    def mostrar_lista():
        ix = open_dir("IndexEventos")
        with ix.searcher() as searcher:
            cat_val = '"' + str(spin.get()) + '"'
            frase_val = str(en.get().strip())
            
            cadena_query = f"categorias:{cat_val}"
            if frase_val:
                cadena_query += f" NOT titulo:\"{frase_val}\""
                
            q = QueryParser("categorias", ix.schema).parse(cadena_query)
            results = searcher.search(q, limit=3)
            imprimir_lista(results)

    v = Toplevel()
    v.title("Categoría y Título")
    l1 = Label(v, text="Seleccione categoría:")
    l1.pack(side=LEFT)

    ix = open_dir("IndexEventos")      
    with ix.searcher() as searcher:
        lista_cats = [i.decode('utf-8') for i in searcher.lexicon('categorias')]

    spin = Spinbox(v, values=lista_cats, state="readonly")
    spin.pack(side=LEFT)

    l2 = Label(v, text="Frase a excluir en título:")
    l2.pack(side=LEFT)
    en = Entry(v, width=40)
    en.pack(side=LEFT)

    b = Button(v, text="Buscar", command=mostrar_lista)
    b.pack(side=LEFT)
    
def buscar_fecha_titulo():
    def mostrar_lista():
        fecha_txt = str(en_fecha.get().strip())
        palabras_txt = str(en_palabras.get().strip())
        
        if re.match(r'^\d{8}$', fecha_txt):
            fecha_obj = datetime.strptime(fecha_txt, "%Y%m%d")
            ix = open_dir("IndexEventos")
            with ix.searcher() as searcher:
                qp = QueryParser("titulo", ix.schema)
                q_titulo = qp.parse(palabras_txt)
                
                q_fecha = query.DateRange("fecha_inicio", None, fecha_obj) & query.DateRange("fecha_fin", fecha_obj, None)
                q_comb = query.And([q_fecha, q_titulo])
                
                results = searcher.search(q_comb, limit=None)
                imprimir_lista(results)
        else:
            messagebox.showerror("ERROR", "Formato de fecha incorrecto. Debe ser AAAAMMDD.")

    v = Toplevel()
    v.title("Fecha y Título")
    l1 = Label(v, text="Fecha (AAAAMMDD):")
    l1.pack(side=LEFT)
    en_fecha = Entry(v, width=15)
    en_fecha.pack(side=LEFT)

    l2 = Label(v, text="Palabras del título:")
    l2.pack(side=LEFT)
    en_palabras = Entry(v, width=30)
    en_palabras.pack(side=LEFT)

    b = Button(v, text="Buscar", command=mostrar_lista)
    b.pack(side=LEFT)
    
def modificar_fechas():
    def procesar_modificacion():
        f_ori_txt = str(en_antigua.get().strip())
        f_nueva_txt = str(en_nueva.get().strip())
        
        if re.match(r'^\d{2}-\d{2}-\d{4}$', f_ori_txt) and re.match(r'^\d{2}-\d{2}-\d{4}$', f_nueva_txt):
            dt_ori = datetime.strptime(f_ori_txt, "%d-%m-%Y")
            dt_nueva = datetime.strptime(f_nueva_txt, "%d-%m-%Y")
            
            ix = open_dir("IndexEventos")
            with ix.searcher() as searcher:
                q = query.Term("fecha_inicio", dt_ori)
                results = searcher.search(q, limit=None)
                count = len(results)
                
                if count > 0:
                    docs_a_modificar = [dict(doc) for doc in results]
                    
                    respuesta = messagebox.askyesno(title="Confirmar Modificación", 
                                                   message=f"Se han encontrado {count} eventos que se celebran en la fecha {f_ori_txt}.\n¿Desea modificar su fecha a {f_nueva_txt}?")
                    if respuesta:
                        writer = ix.writer()
                        for doc in docs_a_modificar:
                            writer.update_document(
                                titulo=doc['titulo'],
                                poblacion=doc['poblacion'],
                                fecha_inicio=dt_nueva,
                                fecha_fin=dt_nueva if doc.get('fecha_fin') == doc.get('fecha_inicio') else doc.get('fecha_fin'),
                                hora=doc['hora'],
                                categorias=doc['categorias'],
                                descripcion=doc.get('descripcion', 'Desconocido')
                            )
                        writer.delete_by_query(q)
                        writer.commit()
                        messagebox.showinfo("Éxito", f"Se han modificado las fechas de {count} eventos.")
                else:
                    messagebox.showinfo("Información", f"No hay ningún evento indexado para la fecha {f_ori_txt}.")
        else:
            messagebox.showerror("ERROR", "Formato de fechas incorrecto. Debe ser DD-MM-AAAA.")

    v = Toplevel()
    v.title("Modificar fechas")
    l1 = Label(v, text="Fecha original (DD-MM-AAAA):")
    l1.pack(side=LEFT)
    en_antigua = Entry(v, width=15)
    en_antigua.pack(side=LEFT)

    l2 = Label(v, text="Fecha nueva (DD-MM-AAAA):")
    l2.pack(side=LEFT)
    en_nueva = Entry(v, width=15)
    en_nueva.pack(side=LEFT)

    b = Button(v, text="Modificar", command=procesar_modificacion)
    b.pack(side=LEFT)
    
def titulo_subcadena():
    def mostrar_lista(event=None):
        cadena = str(en.get().strip())
        if " " in cadena or not cadena:
            messagebox.showerror("ERROR", "La cadena introducida no debe contener espacios ni estar vacía.")
            return

        ix = open_dir("IndexEventos")
        with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
            q = query.Prefix("titulo", cadena.lower())
            results = searcher.search(q, limit=5)
            
            v_res = Toplevel()
            v_res.title("Resultados Subcadena Título")
            sc = Scrollbar(v_res)
            sc.pack(side=RIGHT, fill=Y)
            lb = Listbox(v_res, width=100, yscrollcommand=sc.set)
            for row in results:
                lb.insert(END, row['titulo'])
            lb.pack(side=LEFT, fill=BOTH)
            sc.config(command=lb.yview)

    v = Toplevel()
    v.title("Título por Subcadena")
    l = Label(v, text="Introduzca cadena (sin espacios):")
    l.pack(side=LEFT)
    en = Entry(v, width=30)
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)
    
def principal():
    raiz = Tk()
    raiz.title("Buscador de Eventos Gastronómicos - Whoosh")
    menu = Menu(raiz)

    # Menú Datos
    menudatos = Menu(menu, tearoff=0)
    menudatos.add_command(label="Cargar", command=cargar)
    menudatos.add_command(label="Listar", command=listar_todos)
    menudatos.add_command(label="Listar eventos noche", command=listar_noche)
    menudatos.add_command(label="Salir", command=raiz.quit)
    menu.add_cascade(label="Datos", menu=menudatos)

    # Menú Buscar
    menubuscar = Menu(menu, tearoff=0)
    menubuscar.add_command(label="Título", command=buscar_titulo)
    menubuscar.add_command(label="Eventos por población", command=buscar_poblacion)
    menubuscar.add_command(label="Categoría y Título", command=buscar_categoria_titulo)
    menubuscar.add_command(label="Fecha y Título", command=buscar_fecha_titulo)
    menubuscar.add_command(label="Modificar fechas", command=modificar_fechas)
    menubuscar.add_command(label="Título por Subcadena", command=titulo_subcadena)
    menu.add_cascade(label="Buscar", menu=menubuscar)

    raiz.config(menu=menu)
    raiz.mainloop()

if __name__ == "__main__":
    principal()