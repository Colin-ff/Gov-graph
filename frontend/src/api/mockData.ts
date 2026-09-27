import type { GraphData, GovernanceGroup } from "../types/governance";

const UUID = {
  // original 6 (kept for mockGroups detail panel)
  council:   "11111111-0001-0000-0000-000000000001",
  acadBoard: "11111111-0002-0000-0000-000000000002",
  eduCmte:   "11111111-0003-0000-0000-000000000003",
  resCmte:   "11111111-0004-0000-0000-000000000004",
  stuCmte:   "11111111-0005-0000-0000-000000000005",
  equityWg:  "11111111-0006-0000-0000-000000000006",

  // reporting to University Council
  auditCmte:   "11111111-0007-0000-0000-000000000007",
  financeCmte: "11111111-0008-0000-0000-000000000008",
  remunCmte:   "11111111-0009-0000-0000-000000000009",
  infraCmte:   "11111111-0010-0000-0000-000000000010",

  // reporting to Academic Board
  gradResCmte:  "11111111-0011-0000-0000-000000000011",
  acadQualCmte: "11111111-0012-0000-0000-000000000012",
  acadStdCmte:  "11111111-0013-0000-0000-000000000013",

  // reporting to Education Committee
  curriculumWg:  "11111111-0014-0000-0000-000000000014",
  onlineLearningWg: "11111111-0015-0000-0000-000000000015",
  assessmentWg:  "11111111-0016-0000-0000-000000000016",

  // reporting to Research Committee
  resEthicsCmte: "11111111-0017-0000-0000-000000000017",
  resInfraWg:    "11111111-0018-0000-0000-000000000018",
  hdrAdvisory:   "11111111-0019-0000-0000-000000000019",
  resIntegrityWg:"11111111-0020-0000-0000-000000000020",

  // reporting to Student Affairs Committee
  wellbeingWg:   "11111111-0021-0000-0000-000000000021",
  intlStudentsAp:"11111111-0022-0000-0000-000000000022",
  stuExpWg:      "11111111-0023-0000-0000-000000000023",

  // reporting to Graduate Research Committee
  hdrScholarshipsWg:"11111111-0024-0000-0000-000000000024",
  gradOutcomesWg:   "11111111-0025-0000-0000-000000000025",

  // reporting to Academic Quality Committee
  ltiWg:        "11111111-0026-0000-0000-000000000026",
  peerReviewAp: "11111111-0027-0000-0000-000000000027",
  accreditWg:   "11111111-0028-0000-0000-000000000028",

  // reporting to Academic Standards Committee
  admissionsWg: "11111111-0029-0000-0000-000000000029",
  progressWg:   "11111111-0030-0000-0000-000000000030",
  gradingWg:    "11111111-0031-0000-0000-000000000031",

  // reporting to Audit & Risk Committee
  internalAuditWg: "11111111-0032-0000-0000-000000000032",
  complianceWg:    "11111111-0033-0000-0000-000000000033",
  riskMgmtWg:     "11111111-0034-0000-0000-000000000034",

  // reporting to Finance Committee
  budgetWg:    "11111111-0035-0000-0000-000000000035",
  investmentAp:"11111111-0036-0000-0000-000000000036",
  procurementWg:"11111111-0037-0000-0000-000000000037",

  // reporting to Infrastructure Committee
  campusPlanWg: "11111111-0038-0000-0000-000000000038",
  itGovWg:      "11111111-0039-0000-0000-000000000039",
  sustainWg:    "11111111-0040-0000-0000-000000000040",

  // orphan nodes (no edges)
  engAdvisory:  "11111111-0041-0000-0000-000000000041",
  artsAdvisory: "11111111-0042-0000-0000-000000000042",
  medAdvisory:  "11111111-0043-0000-0000-000000000043",
  bizAdvisory:  "11111111-0044-0000-0000-000000000044",
  sciAdvisory:  "11111111-0045-0000-0000-000000000045",
  libraryAdv:   "11111111-0046-0000-0000-000000000046",
  alumniAp:     "11111111-0047-0000-0000-000000000047",
  industryEngCmte: "11111111-0048-0000-0000-000000000048",
  communityAp:  "11111111-0049-0000-0000-000000000049",
  emeritusFac:  "11111111-0050-0000-0000-000000000050",
};

export const mockGraphData: GraphData = {
  nodes: [
    { uuid: UUID.council,         group_name: "University Council" },
    { uuid: UUID.acadBoard,       group_name: "Academic Board" },
    { uuid: UUID.eduCmte,         group_name: "Education Committee" },
    { uuid: UUID.resCmte,         group_name: "Research Committee" },
    { uuid: UUID.stuCmte,         group_name: "Student Affairs Committee" },
    { uuid: UUID.equityWg,        group_name: "Equity & Diversity WG" },
    { uuid: UUID.auditCmte,       group_name: "Audit & Risk Committee" },
    { uuid: UUID.financeCmte,     group_name: "Finance Committee" },
    { uuid: UUID.remunCmte,       group_name: "Remuneration Committee" },
    { uuid: UUID.infraCmte,       group_name: "Infrastructure Committee" },
    { uuid: UUID.gradResCmte,     group_name: "Graduate Research Committee" },
    { uuid: UUID.acadQualCmte,    group_name: "Academic Quality Committee" },
    { uuid: UUID.acadStdCmte,     group_name: "Academic Standards Committee" },
    { uuid: UUID.curriculumWg,    group_name: "Curriculum Review WG" },
    { uuid: UUID.onlineLearningWg,group_name: "Online Learning WG" },
    { uuid: UUID.assessmentWg,    group_name: "Assessment Reform WG" },
    { uuid: UUID.resEthicsCmte,   group_name: "Research Ethics Committee" },
    { uuid: UUID.resInfraWg,      group_name: "Research Infrastructure WG" },
    { uuid: UUID.hdrAdvisory,     group_name: "HDR Advisory Panel" },
    { uuid: UUID.resIntegrityWg,  group_name: "Research Integrity WG" },
    { uuid: UUID.wellbeingWg,     group_name: "Student Wellbeing WG" },
    { uuid: UUID.intlStudentsAp,  group_name: "International Students Advisory Panel" },
    { uuid: UUID.stuExpWg,        group_name: "Student Experience WG" },
    { uuid: UUID.hdrScholarshipsWg,group_name: "HDR Scholarships WG" },
    { uuid: UUID.gradOutcomesWg,  group_name: "Graduate Outcomes WG" },
    { uuid: UUID.ltiWg,           group_name: "Learning & Teaching Innovation WG" },
    { uuid: UUID.peerReviewAp,    group_name: "Academic Peer Review Panel" },
    { uuid: UUID.accreditWg,      group_name: "Accreditation WG" },
    { uuid: UUID.admissionsWg,    group_name: "Admissions Review WG" },
    { uuid: UUID.progressWg,      group_name: "Progression & Awards WG" },
    { uuid: UUID.gradingWg,       group_name: "Grading & Assessment WG" },
    { uuid: UUID.internalAuditWg, group_name: "Internal Audit WG" },
    { uuid: UUID.complianceWg,    group_name: "Compliance WG" },
    { uuid: UUID.riskMgmtWg,      group_name: "Risk Management WG" },
    { uuid: UUID.budgetWg,        group_name: "Budget Planning WG" },
    { uuid: UUID.investmentAp,    group_name: "Investment Advisory Panel" },
    { uuid: UUID.procurementWg,   group_name: "Procurement WG" },
    { uuid: UUID.campusPlanWg,    group_name: "Campus Planning WG" },
    { uuid: UUID.itGovWg,         group_name: "IT Governance WG" },
    { uuid: UUID.sustainWg,       group_name: "Sustainability WG" },
    // orphans
    { uuid: UUID.engAdvisory,     group_name: "Faculty of Engineering Advisory Panel" },
    { uuid: UUID.artsAdvisory,    group_name: "Faculty of Arts Advisory Panel" },
    { uuid: UUID.medAdvisory,     group_name: "Faculty of Medicine Advisory Panel" },
    { uuid: UUID.bizAdvisory,     group_name: "Faculty of Business Advisory Panel" },
    { uuid: UUID.sciAdvisory,     group_name: "Faculty of Science Advisory Panel" },
    { uuid: UUID.libraryAdv,      group_name: "Library Advisory Committee" },
    { uuid: UUID.alumniAp,        group_name: "Alumni Advisory Panel" },
    { uuid: UUID.industryEngCmte, group_name: "Industry Engagement Committee" },
    { uuid: UUID.communityAp,     group_name: "Community Relations Advisory Panel" },
    { uuid: UUID.emeritusFac,     group_name: "Emeritus Faculty Advisory Panel" },
  ],
  relations: [
    // → University Council
    { source_uuid: UUID.acadBoard,    target_uuid: UUID.council,      relation_type: "Reports to", directed: true },
    { source_uuid: UUID.auditCmte,    target_uuid: UUID.council,      relation_type: "Reports to", directed: true },
    { source_uuid: UUID.financeCmte,  target_uuid: UUID.council,      relation_type: "Reports to", directed: true },
    { source_uuid: UUID.remunCmte,    target_uuid: UUID.council,      relation_type: "Reports to", directed: true },
    { source_uuid: UUID.infraCmte,    target_uuid: UUID.council,      relation_type: "Reports to", directed: true },
    // → Academic Board
    { source_uuid: UUID.eduCmte,      target_uuid: UUID.acadBoard,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.resCmte,      target_uuid: UUID.acadBoard,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.stuCmte,      target_uuid: UUID.acadBoard,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.gradResCmte,  target_uuid: UUID.acadBoard,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.acadQualCmte, target_uuid: UUID.acadBoard,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.acadStdCmte,  target_uuid: UUID.acadBoard,    relation_type: "Reports to", directed: true },
    // → Education Committee
    { source_uuid: UUID.curriculumWg,    target_uuid: UUID.eduCmte,   relation_type: "Reports to", directed: true },
    { source_uuid: UUID.onlineLearningWg,target_uuid: UUID.eduCmte,   relation_type: "Reports to", directed: true },
    { source_uuid: UUID.assessmentWg,    target_uuid: UUID.eduCmte,   relation_type: "Reports to", directed: true },
    { source_uuid: UUID.equityWg,        target_uuid: UUID.eduCmte,   relation_type: "Reports to", directed: true },
    // → Research Committee
    { source_uuid: UUID.resEthicsCmte,  target_uuid: UUID.resCmte,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.resInfraWg,     target_uuid: UUID.resCmte,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.hdrAdvisory,    target_uuid: UUID.resCmte,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.resIntegrityWg, target_uuid: UUID.resCmte,    relation_type: "Reports to", directed: true },
    // → Student Affairs Committee
    { source_uuid: UUID.wellbeingWg,    target_uuid: UUID.stuCmte,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.intlStudentsAp, target_uuid: UUID.stuCmte,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.stuExpWg,       target_uuid: UUID.stuCmte,    relation_type: "Reports to", directed: true },
    // → Graduate Research Committee
    { source_uuid: UUID.hdrScholarshipsWg,target_uuid: UUID.gradResCmte, relation_type: "Reports to", directed: true },
    { source_uuid: UUID.gradOutcomesWg,   target_uuid: UUID.gradResCmte, relation_type: "Reports to", directed: true },
    // → Academic Quality Committee
    { source_uuid: UUID.ltiWg,       target_uuid: UUID.acadQualCmte,  relation_type: "Reports to", directed: true },
    { source_uuid: UUID.peerReviewAp,target_uuid: UUID.acadQualCmte,  relation_type: "Reports to", directed: true },
    { source_uuid: UUID.accreditWg,  target_uuid: UUID.acadQualCmte,  relation_type: "Reports to", directed: true },
    // → Academic Standards Committee
    { source_uuid: UUID.admissionsWg,target_uuid: UUID.acadStdCmte,   relation_type: "Reports to", directed: true },
    { source_uuid: UUID.progressWg,  target_uuid: UUID.acadStdCmte,   relation_type: "Reports to", directed: true },
    { source_uuid: UUID.gradingWg,   target_uuid: UUID.acadStdCmte,   relation_type: "Reports to", directed: true },
    // → Audit & Risk Committee
    { source_uuid: UUID.internalAuditWg,target_uuid: UUID.auditCmte,  relation_type: "Reports to", directed: true },
    { source_uuid: UUID.complianceWg,   target_uuid: UUID.auditCmte,  relation_type: "Reports to", directed: true },
    { source_uuid: UUID.riskMgmtWg,     target_uuid: UUID.auditCmte,  relation_type: "Reports to", directed: true },
    // → Finance Committee
    { source_uuid: UUID.budgetWg,     target_uuid: UUID.financeCmte,  relation_type: "Reports to", directed: true },
    { source_uuid: UUID.investmentAp, target_uuid: UUID.financeCmte,  relation_type: "Reports to", directed: true },
    { source_uuid: UUID.procurementWg,target_uuid: UUID.financeCmte,  relation_type: "Reports to", directed: true },
    // → Infrastructure Committee
    { source_uuid: UUID.campusPlanWg, target_uuid: UUID.infraCmte,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.itGovWg,      target_uuid: UUID.infraCmte,    relation_type: "Reports to", directed: true },
    { source_uuid: UUID.sustainWg,    target_uuid: UUID.infraCmte,    relation_type: "Reports to", directed: true },
    // cross-cutting collaborations
    { source_uuid: UUID.itGovWg,      target_uuid: UUID.resInfraWg,   relation_type: "Reports to", directed: true },
    { source_uuid: UUID.wellbeingWg,  target_uuid: UUID.equityWg,     relation_type: "Reports to", directed: true },
  ],
};

export const mockGroups: Record<string, GovernanceGroup> = {
  [UUID.council]: {
    uuid: UUID.council,
    group_name: "University Council",
    entity_type: "Board",
    status: "active",
    purpose: "The governing authority of UNSW, responsible for overall direction and supervision of the university.",
    responsibilities: "Oversees financial accountability, strategic direction, and senior executive appointments.",
    start_date: "2023-01-01",
    review_date: "2027-01-01",
    can_view_meetings: true,
    meeting_frequency_per_year: 6,
    meeting_duration_hour: 3,
    membership: [
      { uuid: "m-001", first_name: "Anne",  last_name: "Simmons", roles: ["Chair"] },
      { uuid: "m-002", first_name: "Mark",  last_name: "Chen",    roles: ["Secretariat"] },
    ],
    relations: [
      { uuid: UUID.acadBoard, group_name: "Academic Board", relation_type: "Report to", direction: "reported_to_by" },
    ],
    reference_links: [
      { title: "ToR", url: "https://sharepoint.unsw.edu.au/tor/university-council" },
    ],
  },
  [UUID.acadBoard]: {
    uuid: UUID.acadBoard,
    group_name: "Academic Board",
    entity_type: "Board",
    status: "active",
    purpose: "Responsible for academic governance including curriculum, assessment standards, and academic quality.",
    responsibilities: "Advises Council on academic policy and quality assurance matters.",
    start_date: "2023-01-01",
    review_date: "2027-01-01",
    can_view_meetings: true,
    meeting_frequency_per_year: 8,
    meeting_duration_hour: 2,
    membership: [
      { uuid: "m-003", first_name: "David", last_name: "Park",   roles: ["Chair"] },
      { uuid: "m-004", first_name: "Julia", last_name: "Reeves", roles: ["Secretariat"] },
    ],
    relations: [
      { uuid: UUID.council,   group_name: "University Council",        relation_type: "Report to", direction: "reports_to" },
      { uuid: UUID.eduCmte,   group_name: "Education Committee",       relation_type: "Report to", direction: "reported_to_by" },
      { uuid: UUID.resCmte,   group_name: "Research Committee",        relation_type: "Report to", direction: "reported_to_by" },
      { uuid: UUID.stuCmte,   group_name: "Student Affairs Committee", relation_type: "Report to", direction: "reported_to_by" },
    ],
    reference_links: [
      { title: "ToR", url: "https://sharepoint.unsw.edu.au/tor/academic-board" },
    ],
  },
  [UUID.eduCmte]: {
    uuid: UUID.eduCmte,
    group_name: "Education Committee",
    entity_type: "Committee",
    status: "active",
    purpose: "Oversees undergraduate and postgraduate coursework programs, learning and teaching quality.",
    responsibilities: "Reports to Academic Board on all matters relating to teaching and learning.",
    start_date: "2023-01-01",
    review_date: "2027-01-01",
    can_view_meetings: true,
    meeting_frequency_per_year: 6,
    meeting_duration_hour: 2,
    membership: [
      { uuid: "m-005", first_name: "Sarah", last_name: "Li",      roles: ["Chair"] },
      { uuid: "m-006", first_name: "Tom",   last_name: "Wallace", roles: ["Secretariat"] },
    ],
    relations: [
      { uuid: UUID.acadBoard, group_name: "Academic Board",       relation_type: "Report to", direction: "reports_to" },
      { uuid: UUID.equityWg,  group_name: "Equity & Diversity WG", relation_type: "Report to", direction: "reported_to_by" },
    ],
    reference_links: [
      { title: "ToR", url: "https://sharepoint.unsw.edu.au/tor/education-committee" },
    ],
  },
  [UUID.resCmte]: {
    uuid: UUID.resCmte,
    group_name: "Research Committee",
    entity_type: "Committee",
    status: "active",
    purpose: "Provides oversight of research strategy, ethics, integrity, and HDR student progress.",
    responsibilities: "Reports to Academic Board on research governance.",
    start_date: "2023-01-01",
    review_date: "2027-01-01",
    can_view_meetings: true,
    meeting_frequency_per_year: 6,
    meeting_duration_hour: 2,
    membership: [
      { uuid: "m-007", first_name: "James", last_name: "Okafor", roles: ["Chair"] },
      { uuid: "m-008", first_name: "Nina",  last_name: "Patel",  roles: ["Secretariat"] },
    ],
    relations: [
      { uuid: UUID.acadBoard, group_name: "Academic Board", relation_type: "Report to", direction: "reports_to" },
    ],
    reference_links: [
      { title: "ToR", url: "https://sharepoint.unsw.edu.au/tor/research-committee" },
    ],
  },
  [UUID.stuCmte]: {
    uuid: UUID.stuCmte,
    group_name: "Student Affairs Committee",
    entity_type: "Committee",
    status: "active",
    purpose: "Advises on student welfare, conduct, and experience matters.",
    responsibilities: "Advises Academic Board on student experience and conduct policy.",
    start_date: "2023-01-01",
    review_date: "2027-01-01",
    can_view_meetings: true,
    meeting_frequency_per_year: 4,
    meeting_duration_hour: 1.5,
    membership: [
      { uuid: "m-009", first_name: "Chloe", last_name: "Burns",  roles: ["Chair"] },
      { uuid: "m-010", first_name: "Raj",   last_name: "Sharma", roles: ["Secretariat"] },
    ],
    relations: [
      { uuid: UUID.acadBoard, group_name: "Academic Board", relation_type: "Report to", direction: "reports_to" },
    ],
    reference_links: [],
  },
  [UUID.equityWg]: {
    uuid: UUID.equityWg,
    group_name: "Equity & Diversity WG",
    entity_type: "Working Group",
    status: "active",
    purpose: "Develops and monitors equity, diversity, and inclusion initiatives across the university.",
    responsibilities: "Works with the Education Committee to embed inclusive curriculum design.",
    start_date: "2023-01-01",
    review_date: "2027-01-01",
    can_view_meetings: true,
    meeting_frequency_per_year: 4,
    meeting_duration_hour: 1,
    membership: [
      { uuid: "m-011", first_name: "Yuki",  last_name: "Tanaka", roles: ["Chair"] },
      { uuid: "m-012", first_name: "Priya", last_name: "Menon",  roles: ["Secretariat"] },
    ],
    relations: [
      { uuid: UUID.eduCmte, group_name: "Education Committee", relation_type: "Report to", direction: "reports_to" },
    ],
    reference_links: [],
  },
};
