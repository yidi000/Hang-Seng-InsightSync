// Mock data for Hang Seng Bank RM Insight Pro Demo

export interface Prospect {
  id: string;
  name: string;
  nameZh: string;
  score: number;
  tier: "A" | "B" | "C";
  priorityLevel?: string;
  opportunityScore?: number;
  riskScore?: number;
  evidenceConfidenceScore?: number;
  scorecardVersion?: string;
  calibrationStatus?: string;
  industry: string;
  region: string;
  focusTags?: string[];
  engagementAngles?: {
    label: string;
    tag: string;
    recommendedTalkTrack: string;
  }[];
  whyPrioritized?: string[];
  recommendedNextStep?: string;
  scoreBreakdown?: Record<string, number>;
  linkageQuality?: {
    directEvidenceRatio?: number;
    scoreableEvidenceRatio?: number;
    contextOnlyEvidenceCount?: number;
    linkageTypeCounts?: Record<string, number>;
  };
  workflowState?: {
    owner?: string | null;
    stage?: string | null;
    status?: string | null;
    reviewStatus?: string | null;
    lastAction?: string | null;
    nextAction?: string | null;
    notes?: string | null;
  };
  backendCompany?: {
    signalCount?: number;
    timelineEventCount?: number;
    activityAt?: string | null;
    updatedAt?: string | null;
  };
  crm?: {
    source: string;
    crmStatus?: string;
    relationshipStage?: string;
    rmOwner?: string | null;
    lastContactedAt?: string | null;
    nextFollowUpAt?: string | null;
    pipelineValue?: number;
    pipelineCurrency?: string;
    estimatedConversionProbability?: number;
    productsHeld?: string[];
    dataQuality?: string;
  };
  contacts?: {
    name: string;
    title: string;
    email: string;
    phone: string;
    source: string;
    confidence: number;
  }[];
  activities?: {
    type: string;
    occurredAt: string;
    summary: string;
    owner: string;
    source: string;
  }[];
  crmOpportunities?: {
    product: string;
    value: number;
    currency: string;
    stage: string;
    probability: number;
    source: string;
  }[];
  productFit: string[];
  entryAngle: string;
  revenue: string;
  employees: string;
  founded: string;
  description: string;
  businessModel: string;
  expansionSignals: string[];
  crossBorderFootprint: string[];
  news: { date: string; title: string; source: string }[];
  bankingNeeds: string[];
  opportunities: { product: string; potential: string; rationale: string }[];
}

export interface TriggerSignal {
  id: string;
  type: "expansion" | "funding" | "policy" | "crossborder";
  title: string;
  company: string;
  date: string;
  summary: string;
  source?: string;
  dataset?: string;
  signalLevel?: string;
  prospectId?: string;
  evidenceRefs?: string[];
  sourceUrl?: string;
}

export const prospects: Prospect[] = [
  {
    id: "p1",
    name: "Shenzhen Greentech Energy Co.",
    nameZh: "深圳绿科能源有限公司",
    score: 92,
    tier: "A",
    industry: "Clean Energy",
    region: "Shenzhen",
    productFit: ["Trade Finance", "FX Hedging", "Cross-border RMB"],
    entryAngle: "Recent Series C funding, expanding into HK market",
    revenue: "HKD 850M",
    employees: "320",
    founded: "2018",
    description: "Leading provider of solar panel manufacturing and installation services across GBA region, specializing in commercial and industrial solar solutions.",
    businessModel: "B2B solar solutions provider with recurring maintenance revenue stream. Key customers include manufacturing facilities and commercial buildings in GBA.",
    expansionSignals: [
      "Announced plan to establish Hong Kong office Q2 2026",
      "Filed trademark applications in Southeast Asian markets",
      "Recruiting senior executives with international experience"
    ],
    crossBorderFootprint: ["Shenzhen (HQ)", "Dongguan (Factory)", "Hong Kong (Planned)"],
    news: [
      { date: "2026-03-15", title: "Greentech Energy closes $50M Series C round", source: "South China Morning Post" },
      { date: "2026-02-28", title: "Shenzhen company wins major solar contract with HK developer", source: "HK Economic Journal" },
      { date: "2026-01-10", title: "GBA clean energy sector sees 40% YoY growth", source: "Caixin Global" }
    ],
    bankingNeeds: [
      "Cross-border payment facilitation for HK expansion",
      "Trade finance for equipment imports",
      "FX risk management as RMB/HKD exposure grows"
    ],
    opportunities: [
      { product: "Cross-border RMB Pool", potential: "HKD 25M annual volume", rationale: "Expanding HK operations will require seamless RMB settlements" },
      { product: "Trade Finance Facility", potential: "HKD 30M facility", rationale: "Solar panel imports from Germany and equipment purchases" },
      { product: "FX Forward Contracts", potential: "HKD 5M annual premium", rationale: "Multi-currency exposure from international suppliers" }
    ]
  },
  {
    id: "p2",
    name: "Guangzhou MediCore Pharmaceuticals",
    nameZh: "广州美迪可医药科技公司",
    score: 88,
    tier: "A",
    industry: "Healthcare",
    region: "Guangzhou",
    productFit: ["Working Capital", "Trade Finance", "M&A Advisory"],
    entryAngle: "IPO preparation, needs sophisticated banking partner",
    revenue: "HKD 1.2B",
    employees: "580",
    founded: "2015",
    description: "Pharmaceutical company focused on generic drug manufacturing and distribution, with growing R&D pipeline for biosimilars.",
    businessModel: "Generic drug manufacturer with distribution network across Southern China. Investing heavily in biosimilar R&D for future growth.",
    expansionSignals: [
      "Engaged investment bank for Hong Kong IPO advisory",
      "Acquired lab facility in Hong Kong Science Park",
      "Signed MOU with European distribution partner"
    ],
    crossBorderFootprint: ["Guangzhou (HQ)", "Foshan (Manufacturing)", "Hong Kong (R&D Lab)"],
    news: [
      { date: "2026-03-10", title: "MediCore Pharma eyes Hong Kong listing in H2 2026", source: "Bloomberg" },
      { date: "2026-02-15", title: "GBA pharma company expands biosimilar research", source: "Reuters" },
      { date: "2026-01-25", title: "Healthcare sector sees increased cross-border investment", source: "HKEJ" }
    ],
    bankingNeeds: [
      "Pre-IPO financing structure",
      "Multi-currency cash management",
      "Letters of Credit for API imports"
    ],
    opportunities: [
      { product: "Pre-IPO Loan Facility", potential: "HKD 100M facility", rationale: "Bridge financing ahead of planned H2 IPO" },
      { product: "Cash Pooling", potential: "HKD 50M daily balance", rationale: "Centralized treasury for GBA operations" },
      { product: "Trade Finance", potential: "HKD 40M LC facility", rationale: "Raw material imports from India and Europe" }
    ]
  },
  {
    id: "p3",
    name: "Hong Kong Digital Solutions Ltd",
    nameZh: "香港数码方案有限公司",
    score: 85,
    tier: "A",
    industry: "Technology",
    region: "Hong Kong",
    productFit: ["Corporate Banking", "Payroll Services", "FX"],
    entryAngle: "Rapid growth, outgrowing current banking setup",
    revenue: "HKD 280M",
    employees: "150",
    founded: "2020",
    description: "Enterprise software company providing cloud-based ERP and CRM solutions to SMEs in Greater China.",
    businessModel: "SaaS subscription model with 85% recurring revenue. Average contract value of HKD 200K annually with 3-year terms.",
    expansionSignals: [
      "Opening Singapore office in Q3 2026",
      "Hiring 50 additional engineers",
      "Signed partnership with major cloud provider"
    ],
    crossBorderFootprint: ["Hong Kong (HQ)", "Shenzhen (Dev Center)", "Singapore (Planned)"],
    news: [
      { date: "2026-03-20", title: "HK tech startup secures government grant for AI development", source: "HK Standard" },
      { date: "2026-03-01", title: "Digital Solutions reports 120% YoY revenue growth", source: "Tech in Asia" },
      { date: "2026-02-10", title: "SaaS companies lead HK tech sector recovery", source: "SCMP" }
    ],
    bankingNeeds: [
      "Scalable corporate banking infrastructure",
      "Multi-currency payroll for regional team",
      "Credit facility for growth investment"
    ],
    opportunities: [
      { product: "Business Account Suite", potential: "HKD 15M average balance", rationale: "Primary banking relationship for fast-growing tech company" },
      { product: "Payroll Services", potential: "150+ employees", rationale: "Growing headcount across multiple jurisdictions" },
      { product: "Working Capital Facility", potential: "HKD 20M facility", rationale: "Support hiring and expansion plans" }
    ]
  },
  {
    id: "p4",
    name: "Foshan Precision Manufacturing",
    nameZh: "佛山精密制造集团",
    score: 78,
    tier: "B",
    industry: "Manufacturing",
    region: "Foshan",
    productFit: ["Trade Finance", "Equipment Finance", "FX Hedging"],
    entryAngle: "Factory upgrade financing opportunity",
    revenue: "HKD 620M",
    employees: "890",
    founded: "2008",
    description: "Precision metal components manufacturer serving automotive and electronics industries.",
    businessModel: "Contract manufacturer with long-term agreements with major automotive OEMs. Investing in automation to improve margins.",
    expansionSignals: [
      "Announced RMB 200M factory automation investment",
      "Won new contract with European auto manufacturer",
      "Exploring Vietnam facility for supply chain diversification"
    ],
    crossBorderFootprint: ["Foshan (HQ & Main Factory)", "Zhongshan (Secondary Plant)"],
    news: [
      { date: "2026-03-05", title: "GBA manufacturers accelerate automation investments", source: "Caixin" },
      { date: "2026-02-20", title: "Foshan firm wins BMW supplier contract", source: "Auto News China" },
      { date: "2026-01-15", title: "Manufacturing sector outlook positive for 2026", source: "China Daily" }
    ],
    bankingNeeds: [
      "Equipment financing for automation",
      "Trade finance for increased export volume",
      "FX management for EUR/RMB exposure"
    ],
    opportunities: [
      { product: "Equipment Finance", potential: "HKD 45M facility", rationale: "Factory automation investment program" },
      { product: "Export LC Facility", potential: "HKD 60M facility", rationale: "Growing European export business" },
      { product: "FX Hedging", potential: "EUR 5M monthly volume", rationale: "New European customer payments" }
    ]
  },
  {
    id: "p5",
    name: "Zhuhai Ocean Logistics Co.",
    nameZh: "珠海远洋物流有限公司",
    score: 75,
    tier: "B",
    industry: "Logistics",
    region: "Zhuhai",
    productFit: ["Trade Finance", "Working Capital", "Insurance"],
    entryAngle: "New shipping routes, needs banking infrastructure",
    revenue: "HKD 430M",
    employees: "260",
    founded: "2012",
    description: "Regional logistics and freight forwarding company specializing in GBA-Southeast Asia routes.",
    businessModel: "Asset-light freight forwarding with owned warehouse facilities. Focus on cross-border e-commerce logistics.",
    expansionSignals: [
      "Launching new Vietnam-Hong Kong shipping route",
      "Building cold chain capability for food logistics",
      "Partnered with major e-commerce platform"
    ],
    crossBorderFootprint: ["Zhuhai (HQ)", "Hong Kong (Operations)", "Shenzhen (Warehouse)"],
    news: [
      { date: "2026-03-12", title: "GBA logistics firms expand Southeast Asia networks", source: "Shipping Gazette" },
      { date: "2026-02-25", title: "E-commerce drives cross-border logistics growth", source: "Logistics Today" },
      { date: "2026-01-30", title: "Cold chain investment surges in Pearl River Delta", source: "SCMP" }
    ],
    bankingNeeds: [
      "Working capital for fleet expansion",
      "Trade finance for customer credit terms",
      "Multi-currency settlement capability"
    ],
    opportunities: [
      { product: "Working Capital Facility", potential: "HKD 35M facility", rationale: "Support fleet and warehouse expansion" },
      { product: "Trade Finance", potential: "HKD 25M facility", rationale: "Offer credit terms to e-commerce customers" },
      { product: "Multi-currency Account", potential: "5 currency pairs", rationale: "Settlement in HKD/RMB/USD/VND/THB" }
    ]
  },
  {
    id: "p6",
    name: "Macau Grand Hospitality Group",
    nameZh: "澳门君悦酒店集团",
    score: 72,
    tier: "B",
    industry: "Hospitality",
    region: "Macau",
    productFit: ["Property Finance", "Cash Management", "Cards"],
    entryAngle: "Expansion into HK, seeking banking partner",
    revenue: "HKD 380M",
    employees: "520",
    founded: "2014",
    description: "Boutique hotel operator with 5 properties in Macau, expanding to Hong Kong market.",
    businessModel: "Hotel management and ownership with focus on mid-to-upper segment. Exploring franchise model for expansion.",
    expansionSignals: [
      "Acquired site in Kowloon for new hotel development",
      "Raising capital for HK expansion",
      "Launched loyalty program across properties"
    ],
    crossBorderFootprint: ["Macau (HQ)", "Hong Kong (Expansion)"],
    news: [
      { date: "2026-03-08", title: "Macau hotel group plans Hong Kong expansion", source: "HK Economic Times" },
      { date: "2026-02-18", title: "GBA tourism recovery boosts hospitality sector", source: "Travel Weekly" },
      { date: "2026-01-20", title: "Boutique hotels see stronger demand post-pandemic", source: "Hotel News" }
    ],
    bankingNeeds: [
      "Project financing for HK development",
      "Cross-border cash management",
      "Corporate card program for staff"
    ],
    opportunities: [
      { product: "Property Development Loan", potential: "HKD 150M facility", rationale: "Finance Kowloon hotel project" },
      { product: "Cash Pooling", potential: "HKD 20M daily balance", rationale: "Centralize treasury across Macau-HK" },
      { product: "Corporate Cards", potential: "200+ cards", rationale: "Staff travel and procurement" }
    ]
  },
  {
    id: "p7",
    name: "Dongguan Smart Electronics",
    nameZh: "东莞智能电子科技公司",
    score: 68,
    tier: "C",
    industry: "Electronics",
    region: "Dongguan",
    productFit: ["Trade Finance", "FX", "Supply Chain Finance"],
    entryAngle: "Supplier to major brands, stable cash flows",
    revenue: "HKD 520M",
    employees: "1,200",
    founded: "2006",
    description: "Consumer electronics manufacturer specializing in smart home devices and wearables.",
    businessModel: "ODM manufacturer for international brands with some own-brand products. Strong relationship with major retailers.",
    expansionSignals: [
      "New R&D center investment",
      "Developing own-brand product line",
      "Exploring Amazon marketplace entry"
    ],
    crossBorderFootprint: ["Dongguan (HQ & Factory)", "Hong Kong (Trading)"],
    news: [
      { date: "2026-03-02", title: "Smart home device demand surges in GBA", source: "Electronics Weekly" },
      { date: "2026-02-12", title: "Dongguan tech firms increase R&D spending", source: "Nanfang Daily" },
      { date: "2026-01-28", title: "Wearables market shows strong growth momentum", source: "IDC" }
    ],
    bankingNeeds: [
      "Supplier payment financing",
      "USD settlement for export proceeds",
      "Supply chain finance for retailers"
    ],
    opportunities: [
      { product: "Supply Chain Finance", potential: "HKD 40M facility", rationale: "Finance receivables from major retailers" },
      { product: "FX Services", potential: "USD 3M monthly volume", rationale: "Export settlement and hedging" },
      { product: "Trade Finance", potential: "HKD 25M facility", rationale: "Component imports from Taiwan/Korea" }
    ]
  },
  {
    id: "p8",
    name: "Zhongshan Furniture Design",
    nameZh: "中山创意家具设计公司",
    score: 65,
    tier: "C",
    industry: "Furniture",
    region: "Zhongshan",
    productFit: ["Trade Finance", "Working Capital"],
    entryAngle: "Growing export business to Europe",
    revenue: "HKD 180M",
    employees: "340",
    founded: "2011",
    description: "High-end furniture manufacturer with focus on sustainable materials and modern design.",
    businessModel: "B2B supplier to furniture retailers and interior design firms. Growing direct-to-consumer online channel.",
    expansionSignals: [
      "Won design awards at Milan Furniture Fair",
      "Launching EU compliance certification",
      "Building showroom in Hong Kong"
    ],
    crossBorderFootprint: ["Zhongshan (HQ & Factory)"],
    news: [
      { date: "2026-02-28", title: "Chinese furniture brands gain traction in Europe", source: "Furniture Today" },
      { date: "2026-02-05", title: "Sustainable furniture demand rises globally", source: "Design Week" },
      { date: "2026-01-18", title: "GBA design sector sees increased investment", source: "HKEJ" }
    ],
    bankingNeeds: [
      "Export financing for European orders",
      "Working capital for inventory",
      "FX management for EUR proceeds"
    ],
    opportunities: [
      { product: "Export Finance", potential: "HKD 15M facility", rationale: "Support growing European order book" },
      { product: "Inventory Finance", potential: "HKD 10M facility", rationale: "Stock buildup for peak seasons" },
      { product: "Business Account", potential: "Multi-currency", rationale: "EUR/USD/RMB settlement needs" }
    ]
  }
];

const curatedTriggerSignals: TriggerSignal[] = [
  {
    id: "ts1",
    type: "expansion",
    title: "Greentech Energy plans Hong Kong office",
    company: "Shenzhen Greentech Energy Co.",
    prospectId: "p1",
    date: "2026-03-15",
    summary: "Clean energy company announces plans to establish Hong Kong regional headquarters, hiring 30+ staff."
  },
  {
    id: "ts2",
    type: "funding",
    title: "MediCore Pharma closes Series C",
    company: "Guangzhou MediCore Pharmaceuticals",
    prospectId: "p2",
    date: "2026-03-10",
    summary: "Healthcare company raises $80M in Series C funding to accelerate IPO timeline and expand R&D."
  },
  {
    id: "ts3",
    type: "policy",
    title: "GBA cross-border facilitation policy",
    company: "Multiple prospects affected",
    date: "2026-03-08",
    summary: "New HKMA guidelines simplify cross-border RMB settlement for GBA businesses."
  },
  {
    id: "ts4",
    type: "crossborder",
    title: "New Vietnam-HK shipping route launched",
    company: "Zhuhai Ocean Logistics Co.",
    prospectId: "p5",
    date: "2026-03-05",
    summary: "Logistics company launches direct shipping service between Vietnam and Hong Kong ports."
  },
  {
    id: "ts5",
    type: "expansion",
    title: "Foshan manufacturer wins BMW contract",
    company: "Foshan Precision Manufacturing",
    prospectId: "p4",
    date: "2026-02-28",
    summary: "Auto parts supplier wins major contract with European automaker, will require capacity expansion."
  },
  {
    id: "ts6",
    type: "funding",
    title: "HK tech startup secures government grant",
    company: "Hong Kong Digital Solutions Ltd",
    prospectId: "p3",
    date: "2026-02-25",
    summary: "Software company receives HKD 10M Innovation and Technology Fund grant for AI development."
  },
  {
    id: "ts7",
    type: "crossborder",
    title: "Macau hotel group acquires HK site",
    company: "Macau Grand Hospitality Group",
    prospectId: "p6",
    date: "2026-02-20",
    summary: "Hospitality company acquires prime Kowloon site for new luxury hotel development."
  },
  {
    id: "ts8",
    type: "policy",
    title: "Green finance incentives announced",
    company: "Multiple prospects affected",
    date: "2026-02-15",
    summary: "Hong Kong government announces enhanced incentives for green and sustainable financing."
  }
];

function signalTypeFromTag(tag: string): TriggerSignal["type"] {
  if (tag.includes("financing")) return "funding";
  if (tag.includes("policy")) return "policy";
  if (tag.includes("cross")) return "crossborder";
  return "expansion";
}

const generatedCompanySignals: TriggerSignal[] = prospects.flatMap((prospect, prospectIndex) =>
  (prospect.focusTags?.length ? prospect.focusTags : prospect.productFit.slice(0, 2)).map(
    (tag, tagIndex) => {
      const type = signalTypeFromTag(tag.toLowerCase());
      const label =
        prospect.engagementAngles?.find((angle) => angle.tag === tag)?.label ||
        tag.replace(/[_-]/g, " ");
      return {
        id: `sample-${prospect.id}-${tagIndex + 1}`,
        type,
        title: `${prospect.name}: ${label} signal`,
        company: prospect.name,
        prospectId: prospect.id,
        date: `2026-03-${String(28 - ((prospectIndex + tagIndex) % 12)).padStart(2, "0")}`,
        summary:
          prospect.engagementAngles?.[tagIndex]?.recommendedTalkTrack ||
          prospect.recommendedNextStep ||
          prospect.entryAngle,
        source: tagIndex === 0 ? "InsightSync" : "CompanyRegistry",
        signalLevel: prospect.tier === "A" ? "high" : "medium",
      };
    }
  )
);

export const triggerSignals: TriggerSignal[] = [
  ...curatedTriggerSignals,
  ...generatedCompanySignals.filter(
    (signal) =>
      !curatedTriggerSignals.some(
        (curated) => curated.prospectId === signal.prospectId && curated.type === signal.type
      )
  ),
];

function distributionBy<T>(
  items: T[],
  getKey: (item: T) => string | undefined
) {
  const counts = items.reduce<Record<string, number>>((acc, item) => {
    const key = getKey(item) || "Others";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name));
}

function companySizeBucket(prospect: Prospect) {
  if (prospect.revenue.includes("B")) return "Large (>HKD 1B)";
  if (prospect.revenue.includes("M")) return "Medium (HKD 100M-1B)";
  return "Unverified";
}

export const marketOverview = {
  industryDistribution: distributionBy(prospects, (prospect) => prospect.industry),
  regionDistribution: distributionBy(prospects, (prospect) => prospect.region),
  companySizeDistribution: distributionBy(prospects, companySizeBucket),
};

export const dashboardStats = {
  leadPoolSize: prospects.length,
  highPriorityProspects: prospects.filter(
    (prospect) => prospect.priorityLevel === "high" || prospect.tier === "A"
  ).length,
  crossBorderOpportunities: prospects.filter((prospect) =>
    prospect.focusTags?.some((tag) =>
      tag.toLowerCase().replace(/[^a-z0-9]/g, "").includes("crossborder")
    )
  ).length,
  financingSignals: triggerSignals.filter((signal) => signal.type === "funding").length,
};
