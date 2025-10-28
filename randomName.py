import random
from typing import Optional, Set

NAME_BANK = {
    "France": {
        "male": ["Lucas","Hugo","Louis","Jules","Adam","Noah","Nathan","Gabriel","Ethan","Tom",
                 "Leo","Arthur","Raphaël","Maxime","Enzo","Alexandre","Théo","Clément","Baptiste","Mathis","Antoine","Paul"],
        "last": ["Martin","Bernard","Dubois","Lefevre","Moreau","Laurent","Faure","Rousseau","Blanc","Henry","Robert","Petit"]
    },
    "Morocco": {
        "male": ["Youssef","Omar","Hamza","Anas","Ilyas","Rayan","Khalid","Mehdi","Ayoub","Ismail",
                 "Soufiane","Abdelaziz","Hicham","Nabil","Reda","Mohammed","Yassine","Tariq","Karim","Achraf","Amine","Said"],
        "last": ["El Fassi","Bennani","El Idrissi","Ouahbi","Chakir","Boukadoum","El Habti","Kabbaj","Alaoui","Najdi","El Mansouri","Zerhouni"]
    },
    "Argentina": {
        "male": ["Mateo","Thiago","Santiago","Juan","Lucas","Benjamín","Joaquín","Bruno","Franco","Emiliano",
                 "Tomás","Agustín","Facundo","Nicolás","Matías","Diego","Gonzalo","Iñaki","Ramiro","Lautaro","Enzo","Martín"],
        "last": ["González","Rodríguez","Gómez","Fernández","López","Díaz","Martínez","Sosa","Pérez","Romero","Álvarez","Torres","Suárez"]
    },
    "Belgium": {
        "male": ["Lars","Arthur","Victor","Noah","Louis","Jens","Matteo","Bram","Milan","Thibault",
                 "Thomas","Elias","Kobe","Robbe","Jasper","Niels","Ruben","Maxim","Julien","Simon","Quentin","Lucas"],
        "last": ["Peeters","Janssens","Maes","Dubois","Claes","Willems","Lemmens","De Smet","Van Damme","De Clercq","Vermeulen","Goossens"]
    },
    "Nigeria": {
        "male": ["Chinedu","Emeka","Ifeanyi","Tunde","Kelechi","Uche","Femi","Sola","Kunle","Tope",
                 "Segun","Yemi","Ayodele","Ade","Bayo","Chibuzo","Ebuka","Nonso","Ola","Chukwuemeka","Obinna","Ikenna"],
        "last": ["Okafor","Adebayo","Olawale","Chukwu","Eze","Balogun","Ibrahim","Ogunleye","Adeniyi","Okoye","Ojo","Adeyemi"]
    },
    "England": {
        "male": ["Oliver","Jack","Harry","George","Oscar","Thomas","James","Alfie","Leo","Charlie",
                 "Henry","Archie","Freddie","Theodore","Isaac","Alexander","Joshua","Edward","Samuel","Max","Finley","Joseph"],
        "last": ["Smith","Jones","Taylor","Brown","Williams","Wilson","Davies","Evans","Thomas","Roberts","Kane","Walker"]
    },
    "Brazil": {
        "male": ["Miguel","Arthur","Heitor","Theo","Davi","Bernardo","Gabriel","Pedro","Enzo","Gustavo",
                 "Lucas","Matheus","Rafael","Cauã","Henrique","João","Eduardo","Felipe","Caio","Luiz","Vitor","Bruno"],
        "last": ["Silva","Santos","Oliveira","Souza","Rodrigues","Ferreira","Almeida","Costa","Pereira","Lima","Gomes","Carvalho"]
    },
    "Colombia": {
        "male": ["Juan","Santiago","Samuel","Daniel","Nicolás","Mateo","Sebastián","Tomás","Emmanuel","Andrés",
                 "Felipe","Julián","Camilo","Miguel","David","Esteban","Brayan","Cristian","Diego","Jorge","Mauricio","Kevin"],
        "last": ["García","Martínez","González","Rodríguez","López","Hernández","Pérez","Sánchez","Ramírez","Torres","Castro","Vargas"]
    },
"Mexico": {
    "male": [
        "Santiago","Mateo","Sebastián","Emiliano","Diego","Leonardo","Daniel","Alejandro","Miguel","Fernando",
        "José","Antonio","Carlos","Luis","Jorge","Ángel","Ricardo","Adrián","Eduardo","Ramón","Iván","Manuel",
        "Cristian","Mauricio","Héctor","Rodrigo"
    ],
    "last": [
        "Hernández","García","Martínez","López","González","Rodríguez","Pérez","Sánchez","Ramírez","Cruz","Flores","Vargas"
    ]
},
    "Uruguay": {
        "male": ["Thiago","Santiago","Bruno","Mateo","Agustín","Benjamín","Emiliano","Diego","Facundo","Juan",
                 "Nicolás","Martín","Matías","Sebastián","Lucas","Federico","Gonzalo","Maximiliano","Franco","Rodrigo","Pablo","Álvaro"],
        "last": ["Pérez","González","Rodríguez","Fernández","Silva","López","Martínez","Suárez","Álvarez","Santos","Cabrera","Perdomo"]
    },
    "Spain": {
        "male": ["Hugo","Martín","Pablo","Lucas","Daniel","Javier","Diego","Álvaro","Sergio","Alejandro",
                 "Adrián","Mario","Raúl","Rubén","Iván","Iker","Gonzalo","Marcos","Óscar","Nicolás","Bruno","Tomás"],
        "last": ["García","Martínez","López","Sánchez","González","Pérez","Fernández","Díaz","Romero","Álvarez","Navarro","Torres"]
    },
    "United States": {
        "male": ["Liam","Noah","William","James","Benjamin","Mason","Elijah","Logan","Alexander","Michael",
                 "Ethan","Daniel","Jacob","Jackson","Sebastian","Aiden","Matthew","Joseph","Samuel","David","Owen","Luke"],
        "last": ["Smith","Johnson","Brown","Williams","Jones","Miller","Davis","Anderson","Wilson","Moore","Taylor","Thomas"]
    },
    "Netherlands": {
        "male": ["Daan","Sem","Finn","Luuk","Thijs","Lars","Jesse","Bram","Milan","Ties",
                 "Niels","Ruben","Sven","Tom","Guus","Koen","Timo","Mees","Max","Jens","Floris","Stijn"],
        "last": ["de Jong","van Dijk","de Vries","van den Berg","Bakker","Visser","Smit","Meijer","Kok","Hendriks","Mulder","Bosch"],
        "prefix": ["van","van der","de","van den"]
    },
    "Italy": {
    "male": [
        "Luca","Marco","Matteo","Giovanni","Francesco","Alessandro","Simone","Andrea",
        "Antonio","Gabriele","Davide","Stefano","Paolo","Riccardo","Leonardo","Pietro",
        "Giulio","Tommaso","Federico","Nicola","Daniele","Salvatore"
    ],
    "last": [
        "Rossi","Russo","Ferrari","Esposito","Bianchi","Romano","Colombo","Ricci","Marino",
        "Greco","Conti","Gallo","Costa","Mancini","Lombardi","Moretti","Barbieri","Rizzo",
        "Giordano","Lombardo","Santoro","De Luca"
    ]
},
    "Chile": {
        "male": ["Benjamín","Matías","Vicente","Agustín","José","Martín","Diego","Tomás","Sebastián","Joaquín",
                 "Felipe","Cristóbal","Franco","Emilio","Andrés","Rafael","Bruno","Mauricio","Nicolás","Ignacio","Gabriel","Hernán"],
        "last": ["González","Muñoz","Rojas","Díaz","Pérez","Soto","Contreras","Silva","Martínez","Hernández","Torres","Vargas"]
    },
    "Germany": {
        "male": ["Lukas","Finn","Leon","Paul","Ben","Noah","Jonas","Maximilian","Elias","Felix",
                 "Moritz","Julian","Tim","Nico","Tobias","Fabian","Philipp","Dominik","Jan","Florian","Marcel","Kevin"],
        "last": ["Müller","Schmidt","Schneider","Fischer","Weber","Meyer","Wagner","Becker","Hoffmann","Schäfer","Koch","Bauer"]
    },
    "Japan": {
        "male": ["Haruto","Yuto","Sota","Ren","Yuki","Kaito","Daiki","Riku","Hiroto","Taiga",
                 "Ryota","Shota","Sora","Itsuki","Kenta","Keita","Yuma","Takumi","Kouki","Naoki","Yuji","Tatsuya"],
        "last": ["Sato","Suzuki","Takahashi","Tanaka","Watanabe","Ito","Yamamoto","Nakamura","Kobayashi","Kato","Yoshida","Yamada"],
        "order": "family_first"
    },
    "Portugal": {
        "male": ["João","Afonso","Rodrigo","Martim","Gonçalo","Duarte","Tiago","Miguel","Rafael","Diogo",
                 "Bernardo","Tomás","Henrique","Vasco","André","Ricardo","Luís","Eduardo","Filipe","Carlos","Rúben","António"],
        "last": ["Silva","Santos","Ferreira","Pereira","Oliveira","Costa","Martins","Rocha","Sousa","Carvalho","Gonçalves","Lopes"]
    },
}


_SYLL = ["al","an","ar","be","da","di","en","el","fa","jo","ka","li","ma","mo","ni","ra","ro","sa","ti","ul","vi"]

def _spanish_double_surnames(last_list):
    a, b = random.sample(last_list, 2)
    return f"{a} {b}"

def _dutch_with_prefix(last_list, prefixes):
    last = random.choice(last_list)
    if random.random() < 0.4 and prefixes:
        return f"{random.choice(prefixes)} {last}"
    return last

def _ensure_unique(name: str, used_names: Optional[Set[str]]) -> str:
    if used_names is None:
        return name
    out = name
    i = 2
    while out in used_names:
        out = f"{name} #{i}"
        i += 1
    used_names.add(out)
    return out

def random_name(nation: str, used_names: Optional[Set[str]] = None) -> str:
    bank = NAME_BANK.get(nation)
    if not bank:
        name = ("X " + "".join(random.choice(_SYLL) for _ in range(2))).title()
        return _ensure_unique(name, used_names)

    first = random.choice(bank["male"])
    if nation in {"Spain","Chile","Colombia","Argentina","Uruguay"}:
        last = _spanish_double_surnames(bank["last"])
    elif nation == "Netherlands":
        last = _dutch_with_prefix(bank["last"], bank.get("prefix", []))
    else:
        last = random.choice(bank["last"])

    full = f"{last} {first}" if bank.get("order") == "family_first" else f"{first} {last}"
    return _ensure_unique(full, used_names)