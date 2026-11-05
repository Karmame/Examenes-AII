import urllib.request
from bs4 import BeautifulSoup
import re
import os
import shutil
from datetime import datetime
from tkinter import *
from tkinter import messagebox

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, DATETIME, ID, KEYWORD
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh import scoring


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
            
            lugar = l1.find('div', class_='block-elto lugar')
            lugar = "".join(lugar.find('div', class_='value').p.stripped_strings) if lugar else "Desconocido"
            
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

            lista.append((titulo, lugar, poblacion, fecha_inicio, fecha_fin, hora, categorias, descripcion))  
    return lista


def cargar():
    if os.path.exists("IndexEventos"):
        if not messagebox.askyesno("Confirmar", "Esta seguro que quiere recargar los datos. \nEsta operación puede ser lenta"):
            return
        shutil.rmtree("IndexEventos")
    os.mkdir("IndexEventos")

    # Esquema: fecha_inicio y fecha_fin las guardaremos como DATETIME para poder comparar y buscar
    schem = Schema(
        titulo=TEXT(stored=True),
        poblacion=ID(stored=True),
        fecha_inicio=DATETIME(stored=True),
        fecha_fin=DATETIME(stored=True),
        hora=ID(stored=True),
        categorias=KEYWORD(stored=True, commas=True, lowercase=True),
        descripcion=TEXT(stored=True)
    )
    
    ix = create_in("IndexEventos", schema=schem)
    writer = ix.writer()
    eventos = extraer_datos()
    contador = 0

    for ev in eventos:
        t, l, p, f_ini, f_fin, h, c, d = ev
        
        # Parseo de fechas DD/MM/AAAA a datetime
        dt_ini = datetime.strptime(f_ini, "%d/%m/%Y") if f_ini else None
        dt_fin = datetime.strptime(f_fin, "%d/%m/%Y") if f_fin else None

        writer.add_document(
            titulo=t, poblacion=p, fecha_inicio=dt_ini, fecha_fin=dt_fin, 
            hora=h, categorias=c, descripcion=d
        )
        contador += 1

    writer.commit()
    messagebox.showinfo("Información", f"Se han indexado {contador} eventos gastronómicos.")

def mostrar_lista(resultados, solo_titulo=False):
    v = Toplevel()
    sc = Scrollbar(v)
    sc.pack(side=RIGHT, fill=Y)
    lb = Listbox(v, width=150, height=20, yscrollcommand=sc.set)
    for r in resultados:
        if solo_titulo:
            lb.insert(END, f"TÍTULO: {r['titulo']}")
        else:
            fi = r['fecha_inicio'].strftime('%d/%m/%Y') if r.get('fecha_inicio') else "N/A"
            ff = r['fecha_fin'].strftime('%d/%m/%Y') if r.get('fecha_fin') else "N/A"
            lb.insert(END, f"TÍTULO: {r['titulo']}")
            lb.insert(END, f"POBLACIÓN: {r['poblacion']} | CATEGORÍAS: {r['categorias']} | HORA: {r['hora']}")
            lb.insert(END, f"FECHA INICIO: {fi} | FECHA FIN: {ff}")
        lb.insert(END, "-"*100)
    lb.pack(side=LEFT, fill=BOTH, expand=True)
    sc.config(command=lb.yview)

def listar_todos():
    ix = open_dir("IndexEventos")
    with ix.searcher() as searcher:
        resultados = list(searcher.documents())
        mostrar_lista(resultados)

def listar_noche():
    ix = open_dir("IndexEventos")
    with ix.searcher() as searcher:
        todos = list(searcher.documents())
        # Filtramos por Python comprobando si la hora es mayor o igual a 20:00
        eventos_noche = []
        for ev in todos:
            hora_str = ev.get('hora', "Desconocido")
            # Extraemos la primera hora que aparezca con formato HH:MM
            match = re.search(r'(\d{2}):(\d{2})', hora_str)
            if match:
                horas = int(match.group(1))
                if horas >= 20:
                    eventos_noche.append(ev)
        mostrar_lista(eventos_noche)

# -----------------------------------------------------------------------------------
# 3. BÚSQUEDAS
# -----------------------------------------------------------------------------------
def buscar_titulo():
    def ejecutar():
        ix = open_dir("IndexEventos")
        with ix.searcher() as searcher:
            query = QueryParser("titulo", ix.schema).parse(en.get())
            resultados = searcher.search(query, limit=15)
            mostrar_lista(resultados)

    v = Toplevel()
    Label(v, text="Palabra/s en título:").pack(side=LEFT)
    en = Entry(v, width=40)
    en.pack(side=LEFT)
    Button(v, text="Buscar", command=ejecutar).pack(side=LEFT)

def buscar_poblacion():
    def ejecutar():
        ix = open_dir("IndexEventos")
        with ix.searcher() as searcher:
            query = QueryParser("poblacion", ix.schema).parse(f'"{spin.get()}"')
            resultados = searcher.search(query, limit=None)
            mostrar_lista(resultados)

    ix = open_dir("IndexEventos")
    with ix.searcher() as searcher:
        poblaciones = [p.decode('utf-8') for p in searcher.lexicon("poblacion")]
    
    v = Toplevel()
    Label(v, text="Seleccione población:").pack(side=LEFT)
    spin = Spinbox(v, values=poblaciones, state="readonly", width=30)
    spin.pack(side=LEFT)
    Button(v, text="Buscar", command=ejecutar).pack(side=LEFT)

def buscar_categoria_titulo():
    def ejecutar():
        ix = open_dir("IndexEventos")
        with ix.searcher() as searcher:
            # Buscar categoría y NOT la frase en el título
            q_str = f'categorias:"{spin.get()}" NOT titulo:"{en.get()}"'
            query = QueryParser("titulo", ix.schema).parse(q_str)
            resultados = searcher.search(query, limit=3)
            mostrar_lista(resultados)

    ix = open_dir("IndexEventos")
    with ix.searcher() as searcher:
        categorias = [c.decode('utf-8') for c in searcher.lexicon("categorias")]
        
    v = Toplevel()
    Label(v, text="Categoría:").pack(side=LEFT)
    spin = Spinbox(v, values=categorias, state="readonly", width=20)
    spin.pack(side=LEFT)
    Label(v, text="Frase excluida (Título):").pack(side=LEFT)
    en = Entry(v, width=30)
    en.pack(side=LEFT)
    Button(v, text="Buscar", command=ejecutar).pack(side=LEFT)

def buscar_fecha_titulo():
    def ejecutar():
        try:
            # Parseamos la fecha AAAAMMDD para Whoosh
            dt = datetime.strptime(en_fecha.get().strip(), "%Y%m%d")
            fecha_busqueda = dt.strftime("%Y%m%d")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha incorrecto. Use AAAAMMDD.")
            return

        ix = open_dir("IndexEventos")
        with ix.searcher() as searcher:
            # Requisito: que se celebren en esa fecha (fecha_inicio <= fecha <= fecha_fin) 
            # y que contengan TODAS las palabras en el título (usamos el default AND)
            q_str = f'fecha_inicio:[TO {fecha_busqueda}] AND fecha_fin:[{fecha_busqueda} TO] AND titulo:({en_palabras.get()})'
            query = QueryParser("titulo", ix.schema).parse(q_str)
            resultados = searcher.search(query, limit=None)
            mostrar_lista(resultados)

    v = Toplevel()
    Label(v, text="Fecha (AAAAMMDD):").pack(side=LEFT)
    en_fecha = Entry(v, width=15)
    en_fecha.pack(side=LEFT)
    Label(v, text="Palabras en Título:").pack(side=LEFT)
    en_palabras = Entry(v, width=30)
    en_palabras.pack(side=LEFT)
    Button(v, text="Buscar", command=ejecutar).pack(side=LEFT)

def modificar_fechas():
    def ejecutar():
        try:
            fecha_antigua = datetime.strptime(en_antigua.get().strip(), "%d-%m-%Y")
            fecha_nueva = datetime.strptime(en_nueva.get().strip(), "%d-%m-%Y")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha incorrecto. Use DD-MM-AAAA.")
            return
            
        ix = open_dir("IndexEventos")
        fecha_ant_str = fecha_antigua.strftime("%Y%m%d")
        
        with ix.searcher() as searcher:
            # Buscamos eventos cuya fecha_inicio coincida
            query = QueryParser("fecha_inicio", ix.schema).parse(fecha_ant_str)
            resultados = searcher.search(query, limit=None)
            total = len(resultados)
            
            if total == 0:
                messagebox.showinfo("Aviso", "No hay eventos en esa fecha.")
                return
                
            if messagebox.askyesno("Confirmar", f"Hay {total} eventos en esta fecha.\n¿Desea modificar sus fechas a {en_nueva.get()}?"):
                # Para actualizar, borramos los documentos originales y los volvemos a insertar con la nueva fecha
                writer = ix.writer()
                for r in resultados:
                    writer.delete_document(r.docnum)
                    writer.add_document(
                        titulo=r['titulo'], poblacion=r['poblacion'],
                        fecha_inicio=fecha_nueva, fecha_fin=r.get('fecha_fin'), 
                        hora=r.get('hora'), categorias=r['categorias'], descripcion=r.get('descripcion')
                    )
                writer.commit()
                messagebox.showinfo("Éxito", "Fechas modificadas correctamente.")

    v = Toplevel()
    Label(v, text="Fecha Antigua (DD-MM-AAAA):").pack(side=LEFT)
    en_antigua = Entry(v, width=15)
    en_antigua.pack(side=LEFT)
    Label(v, text="Fecha Nueva (DD-MM-AAAA):").pack(side=LEFT)
    en_nueva = Entry(v, width=15)
    en_nueva.pack(side=LEFT)
    Button(v, text="Modificar", command=ejecutar).pack(side=LEFT)

def titulo_subcadena():
    def ejecutar():
        texto = en.get().strip()
        if " " in texto:
            messagebox.showerror("Error", "La subcadena no puede contener espacios.")
            return
            
        ix = open_dir("IndexEventos")
        # Usamos scoring.TF_IDF() como algoritmo de ranking
        with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
            # El asterisco al final permite buscar palabras que comiencen con esa subcadena
            query = QueryParser("titulo", ix.schema).parse(f"{texto}*")
            resultados = searcher.search(query, limit=5)
            mostrar_lista(resultados, solo_titulo=True)

    v = Toplevel()
    Label(v, text="Comienza por (sin espacios):").pack(side=LEFT)
    en = Entry(v, width=25)
    en.pack(side=LEFT)
    Button(v, text="Buscar", command=ejecutar).pack(side=LEFT)

# -----------------------------------------------------------------------------------
# 4. VENTANA PRINCIPAL
# -----------------------------------------------------------------------------------
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