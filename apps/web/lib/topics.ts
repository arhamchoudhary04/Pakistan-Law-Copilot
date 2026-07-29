// Curated map of everyday legal topics -> the statutes that cover them, with
// example questions that deep-link into the chat. Kept in sync with the corpus
// (data/corpus). Purely presentational; the answers still come from retrieval.

export interface Topic {
  id: string;
  title: string;
  blurb: string;
  acts: string[];
  examples: string[];
}

export const TOPICS: Topic[] = [
  {
    id: "fundamental-rights",
    title: "Fundamental Rights",
    blurb: "The basic rights the Constitution guarantees every citizen.",
    acts: ["Constitution of Pakistan (Arts. 8–28)"],
    examples: [
      "What fundamental rights does the Constitution guarantee?",
      "Do I have a right to a fair trial?",
      "Is there a right to education in Pakistan?",
    ],
  },
  {
    id: "arrest-police",
    title: "Arrest & Police",
    blurb: "Your rights on arrest, detention, and bail.",
    acts: ["Code of Criminal Procedure, 1898"],
    examples: [
      "What are my rights if I am arrested by the police?",
      "How long can the police detain me without a magistrate?",
      "What is the difference between a bailable and non-bailable offence?",
    ],
  },
  {
    id: "crimes-punishments",
    title: "Crimes & Punishments",
    blurb: "Offences and their penalties under the Penal Code.",
    acts: ["Pakistan Penal Code, 1860"],
    examples: [
      "What is the punishment for theft under the Penal Code?",
      "What counts as criminal breach of trust?",
      "What is the punishment for causing hurt?",
    ],
  },
  {
    id: "marriage-divorce",
    title: "Marriage & Divorce",
    blurb: "Talaq, khula, and dissolution of a Muslim marriage.",
    acts: ["Muslim Family Laws Ordinance, 1961", "Dissolution of Muslim Marriages Act, 1939"],
    examples: [
      "What is the procedure after a husband pronounces talaq?",
      "On what grounds can a woman seek dissolution of her marriage?",
      "Does a divorce need to be registered?",
    ],
  },
  {
    id: "custody-guardianship",
    title: "Child Custody & Guardianship",
    blurb: "Who a child lives with, and who is their legal guardian.",
    acts: ["Guardians and Wards Act, 1890", "Family Courts Act, 1964"],
    examples: [
      "What does a court consider when deciding a child's custody?",
      "Who can apply to be appointed a child's guardian?",
      "Which court hears custody and maintenance disputes?",
    ],
  },
  {
    id: "false-accusation",
    title: "False Accusation & Defamation",
    blurb: "Protection against false charges and damage to reputation.",
    acts: ["Pakistan Penal Code, 1860", "Offence of Qazf Ordinance, 1979"],
    examples: [
      "What is the punishment for making a false criminal charge?",
      "What is qazf, a false accusation of zina?",
      "What counts as defamation under the law?",
    ],
  },
  {
    id: "dowry",
    title: "Dowry & Bridal Gifts",
    blurb: "Legal limits on dowry and bridal gifts.",
    acts: ["Dowry and Bridal Gifts (Restriction) Act, 1976"],
    examples: [
      "Is there a legal limit on the dowry given in a marriage?",
      "Do dowry and bridal gifts have to be listed?",
    ],
  },
  {
    id: "cybercrime",
    title: "Cybercrime",
    blurb: "Online offences under the electronic crimes law.",
    acts: ["Prevention of Electronic Crimes Act, 2016"],
    examples: [
      "What is the punishment for unauthorised access to a computer system?",
      "Is sharing someone's private pictures without consent a crime?",
      "What is cyberstalking under PECA?",
    ],
  },
  {
    id: "harassment",
    title: "Harassment at Work",
    blurb: "Protection against harassment in the workplace.",
    acts: ["Protection against Harassment of Women at the Workplace Act, 2010"],
    examples: [
      "What counts as harassment at the workplace?",
      "How do I file a workplace harassment complaint?",
    ],
  },
  {
    id: "rti",
    title: "Right to Information",
    blurb: "Requesting information held by public bodies.",
    acts: ["Right of Access to Information Act, 2017"],
    examples: [
      "How do I request information from a government department?",
      "Can a public body refuse an information request?",
    ],
  },
  {
    id: "rent",
    title: "Rent & Tenancy",
    blurb: "Rights of tenants and landlords over rented premises.",
    acts: ["Punjab Rented Premises Act, 2009"],
    examples: [
      "On what grounds can a landlord evict a tenant?",
      "Can a landlord increase the rent whenever they want?",
    ],
  },
  {
    id: "consumer",
    title: "Consumer Rights",
    blurb: "Remedies for defective goods and services.",
    acts: ["Punjab Consumer Protection Act, 2005"],
    examples: [
      "What are my rights if I buy a defective product?",
      "Can I claim compensation for a faulty service?",
    ],
  },
  {
    id: "employment",
    title: "Employment",
    blurb: "Terms of service, termination, and workers' rights.",
    acts: ["Industrial and Commercial Employment (Standing Orders) Ordinance, 1968"],
    examples: [
      "Can my employer terminate me without notice?",
      "Am I entitled to a service certificate when I leave a job?",
    ],
  },
  {
    id: "contracts",
    title: "Contracts",
    blurb: "When an agreement is binding, and what breach entitles you to.",
    acts: ["Contract Act, 1872"],
    examples: [
      "What makes an agreement a valid, enforceable contract?",
      "What is the remedy when a contract is breached?",
    ],
  },
];
