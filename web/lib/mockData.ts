export type Transaction = {
  id: string;
  merchant: string;
  category: string;
  amount: number;
  date: string;
  initial: string;
  badgeColor: string;
};

export const recentTransactions: Transaction[] = [
  {
    id: "spotify",
    merchant: "Spotify",
    category: "Servicios y facturas",
    amount: -18.98,
    date: "10 nov",
    initial: "S",
    badgeColor: "bg-emerald-500",
  },
  {
    id: "chick-fil-a",
    merchant: "Chick-fil-A",
    category: "Comida y bebida",
    amount: -20.4,
    date: "8 nov",
    initial: "C",
    badgeColor: "bg-rose-500",
  },
  {
    id: "netflix",
    merchant: "Netflix",
    category: "Servicios y facturas",
    amount: -9.96,
    date: "6 nov",
    initial: "N",
    badgeColor: "bg-red-600",
  },
  {
    id: "hulu",
    merchant: "Hulu",
    category: "Servicios y facturas",
    amount: -8.98,
    date: "4 nov",
    initial: "H",
    badgeColor: "bg-green-600",
  },
  {
    id: "walmart",
    merchant: "Walmart",
    category: "Supermercado",
    amount: -40.24,
    date: "3 nov",
    initial: "W",
    badgeColor: "bg-sky-500",
  },
  {
    id: "mcdonalds",
    merchant: "McDonald's",
    category: "Comida y bebida",
    amount: -10.4,
    date: "31 oct",
    initial: "M",
    badgeColor: "bg-amber-500",
  },
  {
    id: "exxon",
    merchant: "Exxon",
    category: "Transporte y combustible",
    amount: -40.0,
    date: "29 oct",
    initial: "E",
    badgeColor: "bg-red-500",
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
    badgeColor: "bg-sky-500",
  },
  {
    id: "chick-fil-a-upcoming",
    merchant: "Chick-fil-A",
    category: "Comida y bebida",
    amount: -8.2,
    date: "14 nov",
    initial: "C",
    badgeColor: "bg-rose-500",
  },
  {
    id: "exxon-upcoming",
    merchant: "Exxon",
    category: "Transporte y combustible",
    amount: -40.0,
    date: "11 nov",
    initial: "E",
    badgeColor: "bg-red-500",
  },
  {
    id: "mcdonalds-upcoming",
    merchant: "McDonald's",
    category: "Comida y bebida",
    amount: -6.3,
    date: "11 nov",
    initial: "M",
    badgeColor: "bg-amber-500",
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
