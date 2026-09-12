export type BadgeColor = "emerald" | "rose" | "red" | "green" | "sky" | "amber";

export type Transaction = {
  id: string;
  merchant: string;
  category: string;
  amount: number;
  date: string;
  initial: string;
  badge: BadgeColor;
};

export const recentTransactions: Transaction[] = [
  {
    id: "spotify",
    merchant: "Spotify",
    category: "Servicios y facturas",
    amount: -18.98,
    date: "10 nov",
    initial: "S",
    badge: "emerald",
  },
  {
    id: "chick-fil-a",
    merchant: "Chick-fil-A",
    category: "Comida y bebida",
    amount: -20.4,
    date: "8 nov",
    initial: "C",
    badge: "rose",
  },
  {
    id: "netflix",
    merchant: "Netflix",
    category: "Servicios y facturas",
    amount: -9.96,
    date: "6 nov",
    initial: "N",
    badge: "red",
  },
  {
    id: "hulu",
    merchant: "Hulu",
    category: "Servicios y facturas",
    amount: -8.98,
    date: "4 nov",
    initial: "H",
    badge: "green",
  },
  {
    id: "walmart",
    merchant: "Walmart",
    category: "Supermercado",
    amount: -40.24,
    date: "3 nov",
    initial: "W",
    badge: "sky",
  },
  {
    id: "mcdonalds",
    merchant: "McDonald's",
    category: "Comida y bebida",
    amount: -10.4,
    date: "31 oct",
    initial: "M",
    badge: "amber",
  },
  {
    id: "exxon",
    merchant: "Exxon",
    category: "Transporte y combustible",
    amount: -40.0,
    date: "29 oct",
    initial: "E",
    badge: "red",
  },
];

export const upcomingTransactions: Transaction[] = [
  {
    id: "walmart-upcoming",
    merchant: "Walmart",
    category: "Supermercado",
    amount: -120.3,
    date: "16 nov",
    initial: "W",
    badge: "sky",
  },
  {
    id: "chick-fil-a-upcoming",
    merchant: "Chick-fil-A",
    category: "Comida y bebida",
    amount: -8.2,
    date: "14 nov",
    initial: "C",
    badge: "rose",
  },
  {
    id: "exxon-upcoming",
    merchant: "Exxon",
    category: "Transporte y combustible",
    amount: -40.0,
    date: "11 nov",
    initial: "E",
    badge: "red",
  },
  {
    id: "mcdonalds-upcoming",
    merchant: "McDonald's",
    category: "Comida y bebida",
    amount: -6.3,
    date: "11 nov",
    initial: "M",
    badge: "amber",
  },
];

export const balanceSummary = {
  balance: 4200.1,
  accountNumberMasked: "•••• 0096",
  routingNumberMasked: "•••• 4210",
};

export const creditWise = {
  score: 790,
  maxScore: 850,
  label: "Excelente",
  updated: "24 nov 2024",
};

export const spending = {
  moneyIn: 3995.47,
  moneyInGoal: 6447.0,
  moneyOut: 3722.68,
};
