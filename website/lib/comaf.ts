/* ─── All Comaf site content in one place ─── */

export const COMPANY = {
  name:      "Comaf Portas",
  tagline:   "Madeiras que constroem histórias",
  founded:   2005,
  cnpj:      "07.713.673/0001-38",
  phone:     "(85) 3290-5255",
  whatsapp:  "5585997410355",
  email:     "comafportas@hotmail.com",
  instagram: "comafportas",
  address: {
    street:   "Rua Coronel Matos Dourado, 228",
    district: "Antonio Bezerra",
    city:     "Fortaleza",
    state:    "CE",
    full:     "Rua Coronel Matos Dourado, 228 — Antonio Bezerra, Fortaleza - CE",
  },
};

/* Unsplash photo IDs — free commercial use */
const UNS = (id: string, w = 1200, q = 85) =>
  `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=${w}&q=${q}`;

export const IMAGES = {
  hero:       UNS("1558618666-fcd25c85cd64", 1920, 90),
  sobre:      UNS("1516455590571-18256e5bb9ff", 900),
  gallery: [
    UNS("1432821596592-e2c18b78144f", 800),
    UNS("1573164713988-8665fc963095", 800),
    UNS("1571607388263-1044f9ea01eb", 800),
    UNS("1585771724684-38269d6639fd", 800),
    UNS("1522444690570-3a44aede8bfa", 800),
    UNS("1615873968403-89e068629265", 800),
  ],
};

export const PRODUCTS = [
  {
    id:          "portas",
    title:       "Portas de Madeira",
    description: "Portas internas e externas em madeiras nobres. Durabilidade, elegância e máxima resistência para sua obra.",
    image:       UNS("1541123437800-1bb1317badc2", 700),
    tag:         "Produto principal",
  },
  {
    id:          "virgas",
    title:       "Virgas e Baldames",
    description: "Madeiras estruturais para construção civil nas maiores variedades e espessuras do mercado.",
    image:       UNS("1504307651254-35680f356dfd", 700),
    tag:         "Construção",
  },
  {
    id:          "tabuas",
    title:       "Tábuas e Ripas",
    description: "Pranchas, tábuas e ripas em diversas bitolas. Ideais para forro, cobertura e acabamento.",
    image:       UNS("1573164713988-8665fc963095", 700),
    tag:         "Acabamento",
  },
  {
    id:          "pisos",
    title:       "Pisos de Madeira",
    description: "Pisos maciços e laminados que transformam qualquer ambiente com calor e sofisticação.",
    image:       UNS("1585771724684-38269d6639fd", 700),
    tag:         "Revestimento",
  },
  {
    id:          "janelas",
    title:       "Janelas e Marcos",
    description: "Esquadrias, marcos e janelas produzidos com madeira selecionada. Acabamento impecável.",
    image:       UNS("1517697471441-d8b5a5b3efb0", 700),
    tag:         "Esquadrias",
  },
  {
    id:          "compensado",
    title:       "Compensado e MDF",
    description: "Chapas compensadas, MDF e madeiras beneficiadas para marcenaria e construção em geral.",
    image:       UNS("1522444690570-3a44aede8bfa", 700),
    tag:         "Chapas",
  },
];

export const STATS = [
  { value: 20,    suffix: "+", label: "Anos de experiência" },
  { value: 5000,  suffix: "+", label: "Clientes atendidos" },
  { value: 100,   suffix: "+", label: "Produtos em estoque" },
  { value: 3000,  suffix: "m²", label: "Área de estoque" },
];

export const DIFERENCIAIS = [
  {
    icon: "◈",
    title: "Estoque amplo",
    description: "Mais de 3.000 m² de área coberta com variedade completa em madeiras e acabamentos.",
  },
  {
    icon: "◎",
    title: "Atendimento exclusivo",
    description: "Profissionais treinados que priorizam atenção e seriedade em cada negociação.",
  },
  {
    icon: "◉",
    title: "Estacionamento próprio",
    description: "Espaço amplo e seguro para seu veículo enquanto você escolhe com tranquilidade.",
  },
  {
    icon: "◈",
    title: "20 anos de tradição",
    description: "Fundada em 2005, construímos nossa reputação com qualidade, respeito e ética.",
  },
];
