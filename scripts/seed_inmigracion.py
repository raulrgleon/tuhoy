#!/usr/bin/env python3
"""Primera tanda de Inmigración y Latinos: textos originales a partir de reportes reales."""
import html
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("daily", "/home/raul/tuhoy/scripts/daily_edition.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)

PIEZAS = [
    {
        "title": "Un juez de Manhattan tumba las detenciones de ICE en los pasillos de inmigración",
        "excerpt": "Castel declara arbitraria la práctica de arrestar a quienes acuden a su cita en 26 Federal Plaza.",
        "canonical": "https://www.courthousenews.com/judge-issues-final-ruling-against-ice-immigration-court-arrest-policy-in-manhattan/",
        "source": "Courthouse News Service",
        "featured": True,
        "html": """
<p>El juez federal P. Kevin Castel, en Manhattan, dio la razón definitiva a grupos de derechos de migrantes: las detenciones de ICE en los pasillos de los tribunales de inmigración de Nueva York son arbitrarias y caprichosas. El auto de 36 páginas, del 1 de octubre, confirma el bloqueo que ya pesaba sobre la agencia salvo excepciones muy tasadas.</p>
<p>Castel escribe que ICE parece no tener «política alguna» sobre esos arrestos y que sus agentes actúan con «discreción sin guía». El Gobierno, anota, ni siquiera argumentó lo contrario. La agencia había sostenido que un memo de mayo de 2025 justificaba la práctica; más tarde admitió en sede judicial que ese memo no cubría los juzgados y se disculpó por un «error material de hecho».</p>
<p>Durante años ICE evitó detener en los juzgados precisamente para no asustar a quien cumple su cita. Videos de 26 Federal Plaza mostraron pasillos con agentes encapuchados. Amy Belsher, de la NYCLU, llamó al fallo «una victoria enorme» para quien necesita acudir a su audiencia sin ser emboscado.</p>
<h2>Contexto</h2>
<p>El caso lo llevaron African Communities Together y The Door. El DHS no contestó de inmediato. TuHoy lo resume porque el precedente de Manhattan ya es la referencia para otras ciudades donde ICE ha usado el juzgado como trampa.</p>
<p>Fuente: Courthouse News Service — <a href="https://www.courthousenews.com/judge-issues-final-ruling-against-ice-immigration-court-arrest-policy-in-manhattan/">courthousenews.com</a></p>
""",
    },
    {
        "title": "Florida avisa: 177.000 inmigrantes con papeles pueden perder el Medicaid",
        "excerpt": "El recorte, vigente desde el 1 de octubre, no apunta a indocumentados: alcanza a asilados, parole y otras categorías legales.",
        "canonical": "https://www.lanacion.com.ar/estados-unidos/florida/es-oficial-se-confirma-la-cifra-de-inmigrantes-que-podrian-ser-excluidos-de-medicaid-en-florida-nid04102026/",
        "source": "LA NACION / Miami Herald",
        "featured": False,
        "html": """
<p>El Departamento de Niños y Familias de Florida identificó a cerca de 177.000 inmigrantes con estatus regular que, a partir de octubre, dejan de cumplir los requisitos federales de Medicaid. La portavoz Anna Holaday confirmó la cifra, recogida por el Miami Herald y LA NACION. El cambio nace de la ley impulsada por Trump conocida como One Big Beautiful Bill Act.</p>
<p>No se trata de indocumentados: esos ya tenían vetado el Medicaid ordinario. La tijera cae sobre refugiados y asilados sin green card, personas con humanitarian parole, ciertos sobrevivientes de violencia y titulares o solicitantes de visa T. Conservan la cobertura federal los residentes permanentes, algunos cubanos y haitianos, y ciudadanos de países COFA.</p>
<p>En agosto el Estado mandó cartas a quien el sistema SAVE no pudo verificar. Quien no respondió perdió el plan al cerrar septiembre. Queda el Medicaid de emergencia, que no sustituye la atención diaria. Scott Darius, de Florida Voices for Health, lo resumió así: el miedo a salir de casa aleja a la gente de lo que necesita, y eso enferma más.</p>
<h2>Contexto</h2>
<p>Organizaciones advierten de bajas por cartas no recibidas o mudanzas, no solo por la letra de la ley. Niños y embarazadas pueden salvarse si el Estado aplica la regla Ichia. TuHoy lo sigue porque el recorte de Florida es el primer recuento grande de un cambio federal que se replica en otros estados.</p>
<p>Fuente: LA NACION, con datos del DCF y KFF Health News — <a href="https://www.lanacion.com.ar/estados-unidos/florida/es-oficial-se-confirma-la-cifra-de-inmigrantes-que-podrian-ser-excluidos-de-medicaid-en-florida-nid04102026/">lanacion.com.ar</a></p>
""",
    },
    {
        "title": "Houston: la muerte de Lorenzo Salgado Araujo enciende el voto latino en Texas",
        "excerpt": "ICE dice que usó la camioneta como arma; testigos lo niegan. El condado ya financia una investigación de 2,5 millones.",
        "canonical": "https://www.nbcnews.com/politics/2026-election/shooting-death-houston-father-igniting-latino-politics-texas-rcna598588",
        "source": "NBC News",
        "featured": False,
        "html": """
<p>Lorenzo Salgado Araujo iba al trabajo en Houston cuando agentes de ICE, en vehículos sin marcar, lo persiguieron. Un oficial le disparó. La agencia afirma que el padre usó la camioneta como arma; los testigos que viajaban con él cuentan otra historia. La comunidad pide justicia y el caso ya pesa sobre el mapa latino de Texas a un mes de las midterms.</p>
<p>El alcalde John Whitmire dijo primero que la policía de Houston no podía investigar. Tras la presión, el fiscal del condado de Harris, Sean Teare, abrió una pesquisa y el gobierno del condado aprobó 2,5 millones de dólares para financiarla. El gobernador Greg Abbott calló una semana y luego respaldó una investigación independiente.</p>
<p>NBC sitúa el tiroteo en una secuencia de operativos que, desde 2025, han alterado la vida cotidiana en Minneapolis, Los Ángeles y Chicago. En una encuesta, el 67% de los posibles votantes latinos dijo que la ofensiva migratoria de Trump se había pasado de la raya, aunque pocos la ponen como su primer tema.</p>
<h2>Contexto</h2>
<p>Salgado Araujo recogía trabajadores en una camioneta blanca. Ese detalle —un padre de camino a la obra— es el que ha movilizado a vecindarios que se sienten señalados. TuHoy lo publica en la sección de Inmigración y Latinos porque el caso ya no es solo un expediente de ICE: es política local.</p>
<p>Fuente: NBC News — <a href="https://www.nbcnews.com/politics/2026-election/shooting-death-houston-father-igniting-latino-politics-texas-rcna598588">nbcnews.com</a></p>
""",
    },
    {
        "title": "Austin: el juez deja preso al repartidor venezolano tiroteado por ICE",
        "excerpt": "Wilber Garcés Pérez, de 28 años, enfrenta hasta 20 años. El disparo no aparece en el video que vio el tribunal.",
        "canonical": "https://www.nbcnews.com/news/us-news/judge-keeps-immigrant-delivery-driver-shot-ice-custody-alleged-assault-rcna600898",
        "source": "NBC News / AP",
        "featured": False,
        "html": """
<p>El juez federal Dustin Howell decidió el 1 de octubre que Wilber Rafael Garcés Pérez, venezolano de 28 años, siga detenido. Lo acusan de agredir a un agente de ICE con el espejo de su coche el 20 de septiembre en Austin, mientras repartía para DoorDash. Si lo condenan, arriesga hasta 20 años. Howell ve riesgo de fuga hacia Venezuela, donde tiene un hijo.</p>
<p>La fiscalía mostró cámara corporal de la parada y un video de un negocio cercano con la persecución por calles residenciales. El disparo mismo no está en esas imágenes. La defensa, de Kate Lincoln-Goldfinch, denuncia que le negaron atención médica por la herida de bala. Un agente iba en otro coche y apagó la cámara durante la cacería.</p>
<p>Garcés Pérez entró en 2024 por CBP One, el sistema de citas de asilo que Biden abrió y Trump cerró el primer día de su segundo mandato. El caso ha encendido Austin y suma otra escena de persecución vehicular al debate sobre cómo ICE detiene en la calle.</p>
<h2>Contexto</h2>
<p>La misma semana, ICE anunció límites —no una prohibición— a quién puede lanzarse a una persecución. TuHoy junta ambas piezas: la norma nueva y el hombre que ya está en el banquillo. Fuente: NBC News y Associated Press — <a href="https://www.nbcnews.com/news/us-news/judge-keeps-immigrant-delivery-driver-shot-ice-custody-alleged-assault-rcna600898">nbcnews.com</a></p>
""",
    },
    {
        "title": "Cinco detenidos a la salida del pavo en Moroni, Utah: los niños faltan a clase",
        "excerpt": "La policía local dice que eran paradas de tráfico con ICE de copiloto. Homeland Security niega una redada en la planta.",
        "canonical": "https://www.sltrib.com/news/2026/10/04/moroni-ice-enforcement-5-people/",
        "source": "The Salt Lake Tribune",
        "featured": False,
        "html": """
<p>En Moroni, un pueblo de unos 1.500 habitantes en Utah, la planta de pavo es el sueldo de generaciones. El 1 de octubre, al salir del turno, trabajadores vieron camionetas marcadas y sin marcar junto a Pitman Farms / Norbest. Al final de la noche, ICE se llevó a cinco personas, según el subjefe de la policía del North Valley, Logan Ludvigson.</p>
<p>Homeland Security dijo el viernes que no hubo un operativo dirigido a la planta. Ludvigson sostiene que los agentes iban de copiloto en paradas rutinarias —exceso de velocidad, un faro fundido— por el condado de Sanpete. En el pueblo, da igual el matiz: familias se quedan en casa aunque tengan papeles. El superintendente O'Dee Hansen registró menos asistencia el jueves y el viernes; un alumno dijo que su padre era uno de los cinco.</p>
<p>Vecinos buscan en Facebook a quién se llevaron y avisan avistamientos en Gunnison. Un trabajador, contó el Sanpete Messenger, se subió al techo de la planta para ver las camionetas.</p>
<h2>Contexto</h2>
<p>Moroni no es Chicago ni Houston. Es un pueblo del pavo donde la detención a la puerta del trabajo vacía el aula. TuHoy lo pone en Inmigración y Latinos porque la ofensiva de 2026 ya no se mide solo en las grandes ciudades.</p>
<p>Fuente: The Salt Lake Tribune — <a href="https://www.sltrib.com/news/2026/10/04/moroni-ice-enforcement-5-people/">sltrib.com</a></p>
""",
    },
]


def main() -> int:
    env = daily.load_env()
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    daily.ensure_tags(ghost)
    known = daily.existing_titles(ghost)
    state = daily.load_state()
    n = 0
    for pieza in PIEZAS:
        if any(daily.similar(pieza["title"], k) for k in known):
            daily.log(f"seed skip {pieza['title']}")
            continue
        img = daily.source_photo(pieza["canonical"]) or daily.commons_image(
            *daily.story_image_queries(pieza["title"], pieza["excerpt"], "inmigracion")
        )
        img_url = cap = None
        if img:
            blob, filename, mime, cap = img
            img_url = ghost.upload_image(blob, filename, mime)
        body = pieza["html"].strip()
        if cap:
            body += f"\n<p><em>{html.escape(cap)}</em></p>"
        payload = {
            "posts": [
                {
                    "title": pieza["title"],
                    "custom_excerpt": pieza["excerpt"],
                    "html": body,
                    "status": "published",
                    "featured": pieza["featured"],
                    "canonical_url": pieza["canonical"],
                    "tags": [{"name": "Inmigración"}, {"name": "Latinos"}, {"name": "Política"}],
                    "feature_image": img_url,
                    "feature_image_caption": cap,
                    "feature_image_alt": pieza["title"],
                    "visibility": "public",
                }
            ]
        }
        code, resp = ghost.post_json("/posts/?source=html", payload)
        if code >= 300:
            daily.log(f"seed fail {code} {resp}")
            continue
        slug = (resp.get("posts") or [{}])[0].get("slug")
        daily.log(f"seed ok {slug}")
        known.append(pieza["title"])
        state["seen_urls"].append(pieza["canonical"])
        state["seen_titles"].append(daily.norm_title(pieza["title"]))
        n += 1
    daily.save_state(state)
    daily.log(f"seed done {n}")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
