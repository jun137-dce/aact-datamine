CREATE TABLE ctgov.browse_conditions (
    id integer NOT NULL,
    nct_id character varying,
    mesh_term character varying,
    downcase_mesh_term character varying,
    mesh_type character varying
);
CREATE TABLE ctgov.browse_interventions (
    id integer NOT NULL,
    nct_id character varying,
    mesh_term character varying,
    downcase_mesh_term character varying,
    mesh_type character varying
);
CREATE TABLE ctgov.facilities (
    id integer NOT NULL,
    nct_id character varying,
    status character varying,
    name character varying,
    city character varying,
    state character varying,
    zip character varying,
    country character varying,
    latitude numeric(10,6),
    longitude numeric(10,6)
);
CREATE TABLE ctgov.conditions (
    id integer NOT NULL,
    nct_id character varying,
    name character varying,
    downcase_name character varying
);
CREATE TABLE ctgov.countries (
    id integer NOT NULL,
    nct_id character varying,
    name character varying,
    removed boolean
);
CREATE TABLE ctgov.design_outcomes (
    id integer NOT NULL,
    nct_id character varying,
    outcome_type character varying,
    measure text,
    time_frame text,
    population character varying,
    description text
);
CREATE TABLE ctgov.design_groups (
    id integer NOT NULL,
    nct_id character varying,
    group_type character varying,
    title character varying,
    description text
);
CREATE TABLE ctgov.id_information (
    id integer NOT NULL,
    nct_id character varying,
    id_source character varying,
    id_value character varying,
    id_type character varying,
    id_type_description character varying,
    id_link character varying
);
CREATE TABLE ctgov.interventions (
    id integer NOT NULL,
    nct_id character varying,
    intervention_type character varying,
    name character varying,
    description text
);
CREATE TABLE ctgov.keywords (
    id integer NOT NULL,
    nct_id character varying,
    name character varying,
    downcase_name character varying
);
CREATE TABLE ctgov.overall_officials (
    id integer NOT NULL,
    nct_id character varying,
    role character varying,
    name character varying,
    affiliation character varying
);
CREATE TABLE ctgov.sponsors (
    id integer NOT NULL,
    nct_id character varying,
    agency_class character varying,
    lead_or_collaborator character varying,
    name character varying
);
CREATE TABLE ctgov.baseline_counts (
    id integer NOT NULL,
    nct_id character varying,
    result_group_id integer,
    ctgov_group_code character varying,
    units character varying,
    scope character varying,
    count integer
);
CREATE TABLE ctgov.baseline_measurements (
    id integer NOT NULL,
    nct_id character varying,
    result_group_id integer,
    ctgov_group_code character varying,
    classification character varying,
    category character varying,
    title character varying,
    description text,
    units character varying,
    param_type character varying,
    param_value character varying,
    param_value_num numeric,
    dispersion_type character varying,
    dispersion_value character varying,
    dispersion_value_num numeric,
    dispersion_lower_limit numeric,
    dispersion_upper_limit numeric,
    explanation_of_na character varying,
    number_analyzed integer,
    number_analyzed_units character varying,
    population_description character varying,
    calculate_percentage character varying
);
CREATE TABLE ctgov.brief_summaries (
    id integer NOT NULL,
    nct_id character varying,
    description text
);
CREATE TABLE ctgov.calculated_values (
    id integer NOT NULL,
    nct_id character varying,
    number_of_facilities integer,
    number_of_nsae_subjects integer,
    number_of_sae_subjects integer,
    registered_in_calendar_year integer,
    nlm_download_date date,
    actual_duration integer,
    were_results_reported boolean DEFAULT false,
    months_to_report_results integer,
    has_us_facility boolean,
    has_single_facility boolean DEFAULT false,
    minimum_age_num integer,
    maximum_age_num integer,
    minimum_age_unit character varying,
    maximum_age_unit character varying,
    number_of_primary_outcomes_to_measure integer,
    number_of_secondary_outcomes_to_measure integer,
    number_of_other_outcomes_to_measure integer
);
CREATE TABLE ctgov.search_results (
    id integer NOT NULL,
    nct_id character varying NOT NULL,
    name character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    "grouping" character varying DEFAULT ''::character varying NOT NULL,
    study_search_id integer
);
CREATE TABLE ctgov.central_contacts (
    id integer NOT NULL,
    nct_id character varying,
    contact_type character varying,
    name character varying,
    phone character varying,
    email character varying,
    phone_extension character varying,
    role character varying
);
CREATE TABLE ctgov.design_group_interventions (
    id integer NOT NULL,
    nct_id character varying,
    design_group_id integer,
    intervention_id integer
);
CREATE TABLE ctgov.designs (
    id integer NOT NULL,
    nct_id character varying,
    allocation character varying,
    intervention_model character varying,
    observational_model character varying,
    primary_purpose character varying,
    time_perspective character varying,
    masking character varying,
    masking_description text,
    intervention_model_description text,
    subject_masked boolean,
    caregiver_masked boolean,
    investigator_masked boolean,
    outcomes_assessor_masked boolean
);
CREATE TABLE ctgov.detailed_descriptions (
    id integer NOT NULL,
    nct_id character varying,
    description text
);
CREATE TABLE ctgov.documents (
    id integer NOT NULL,
    nct_id character varying,
    document_id character varying,
    document_type character varying,
    url character varying,
    comment text
);
CREATE TABLE ctgov.drop_withdrawals (
    id integer NOT NULL,
    nct_id character varying,
    result_group_id integer,
    ctgov_group_code character varying,
    period character varying,
    reason character varying,
    count integer,
    drop_withdraw_comment character varying,
    reason_comment character varying,
    count_units integer
);
CREATE TABLE ctgov.eligibilities (
    id integer NOT NULL,
    nct_id character varying,
    sampling_method character varying,
    gender character varying,
    minimum_age character varying,
    maximum_age character varying,
    healthy_volunteers boolean,
    population text,
    criteria text,
    gender_description text,
    gender_based boolean,
    adult boolean,
    child boolean,
    older_adult boolean
);
CREATE TABLE ctgov.facility_contacts (
    id integer NOT NULL,
    nct_id character varying,
    facility_id integer,
    contact_type character varying,
    name character varying,
    email character varying,
    phone character varying,
    phone_extension character varying
);
CREATE TABLE ctgov.facility_investigators (
    id integer NOT NULL,
    nct_id character varying,
    facility_id integer,
    role character varying,
    name character varying
);
CREATE TABLE ctgov.intervention_other_names (
    id integer NOT NULL,
    nct_id character varying,
    intervention_id integer,
    name character varying
);
CREATE TABLE ctgov.ipd_information_types (
    id integer NOT NULL,
    nct_id character varying,
    name character varying
);
CREATE TABLE ctgov.links (
    id integer NOT NULL,
    nct_id character varying,
    url character varying,
    description text
);
CREATE TABLE ctgov.mesh_headings (
    id integer NOT NULL,
    qualifier character varying,
    heading character varying,
    subcategory character varying
);
CREATE TABLE ctgov.mesh_terms (
    id integer NOT NULL,
    qualifier character varying,
    tree_number character varying,
    description character varying,
    mesh_term character varying,
    downcase_mesh_term character varying
);
CREATE TABLE ctgov.milestones (
    id integer NOT NULL,
    nct_id character varying,
    result_group_id integer,
    ctgov_group_code character varying,
    title character varying,
    period character varying,
    description text,
    count integer,
    milestone_description character varying,
    count_units character varying
);
CREATE TABLE ctgov.outcome_analyses (
    id integer NOT NULL,
    nct_id character varying,
    outcome_id integer,
    non_inferiority_type character varying,
    non_inferiority_description text,
    param_type character varying,
    param_value numeric,
    dispersion_type character varying,
    dispersion_value numeric,
    p_value_modifier character varying,
    p_value double precision,
    ci_n_sides character varying,
    ci_percent numeric,
    ci_lower_limit numeric,
    ci_upper_limit numeric,
    ci_upper_limit_na_comment character varying,
    p_value_description character varying,
    method character varying,
    method_description text,
    estimate_description text,
    groups_description text,
    other_analysis_description text,
    ci_upper_limit_raw character varying,
    ci_lower_limit_raw character varying,
    p_value_raw character varying
);
CREATE TABLE ctgov.outcome_analysis_groups (
    id integer NOT NULL,
    nct_id character varying,
    outcome_analysis_id integer,
    result_group_id integer,
    ctgov_group_code character varying
);
CREATE TABLE ctgov.outcome_counts (
    id integer NOT NULL,
    nct_id character varying,
    outcome_id integer,
    result_group_id integer,
    ctgov_group_code character varying,
    scope character varying,
    units character varying,
    count integer
);
CREATE TABLE ctgov.outcome_measurements (
    id integer NOT NULL,
    nct_id character varying,
    outcome_id integer,
    result_group_id integer,
    ctgov_group_code character varying,
    classification character varying,
    category character varying,
    title character varying,
    description text,
    units character varying,
    param_type character varying,
    param_value character varying,
    param_value_num numeric,
    dispersion_type character varying,
    dispersion_value character varying,
    dispersion_value_num numeric,
    dispersion_lower_limit numeric,
    dispersion_upper_limit numeric,
    explanation_of_na text,
    dispersion_upper_limit_raw character varying,
    dispersion_lower_limit_raw character varying
);
CREATE TABLE ctgov.outcomes (
    id integer NOT NULL,
    nct_id character varying,
    outcome_type character varying,
    title text,
    description text,
    time_frame text,
    population text,
    anticipated_posting_date date,
    anticipated_posting_month_year character varying,
    units character varying,
    units_analyzed character varying,
    dispersion_type character varying,
    param_type character varying
);
CREATE TABLE ctgov.participant_flows (
    id integer NOT NULL,
    nct_id character varying,
    recruitment_details text,
    pre_assignment_details text,
    units_analyzed character varying
);
CREATE TABLE ctgov.pending_results (
    id integer NOT NULL,
    nct_id character varying,
    event character varying,
    event_date_description character varying,
    event_date date
);
CREATE TABLE ctgov.provided_documents (
    id integer NOT NULL,
    nct_id character varying,
    document_type character varying,
    has_protocol boolean,
    has_icf boolean,
    has_sap boolean,
    document_date date,
    url character varying
);
CREATE TABLE ctgov.reported_event_totals (
    id integer NOT NULL,
    nct_id character varying NOT NULL,
    ctgov_group_code character varying NOT NULL,
    event_type character varying,
    classification character varying NOT NULL,
    subjects_affected integer,
    subjects_at_risk integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);
CREATE TABLE ctgov.reported_events (
    id integer NOT NULL,
    nct_id character varying,
    result_group_id integer,
    ctgov_group_code character varying,
    time_frame text,
    event_type character varying,
    default_vocab character varying,
    default_assessment character varying,
    subjects_affected integer,
    subjects_at_risk integer,
    description text,
    event_count integer,
    organ_system character varying,
    adverse_event_term character varying,
    frequency_threshold integer,
    vocab character varying,
    assessment character varying
);
CREATE TABLE ctgov.responsible_parties (
    id integer NOT NULL,
    nct_id character varying,
    responsible_party_type character varying,
    name character varying,
    title character varying,
    organization character varying,
    affiliation text,
    old_name_title character varying
);
CREATE TABLE ctgov.result_agreements (
    id integer NOT NULL,
    nct_id character varying,
    pi_employee boolean,
    agreement text,
    restriction_type character varying,
    other_details text,
    restrictive_agreement boolean
);
CREATE TABLE ctgov.result_contacts (
    id integer NOT NULL,
    nct_id character varying,
    organization character varying,
    name character varying,
    phone character varying,
    email character varying,
    extension character varying
);
CREATE TABLE ctgov.result_groups (
    id integer NOT NULL,
    nct_id character varying,
    ctgov_group_code character varying,
    result_type character varying,
    title character varying,
    description text,
    outcome_id integer
);
CREATE TABLE ctgov.retractions (
    id bigint NOT NULL,
    reference_id integer,
    pmid character varying,
    source character varying,
    nct_id character varying
);
CREATE TABLE ctgov.search_term_results (
    id bigint NOT NULL,
    nct_id character varying NOT NULL,
    search_term_id bigint NOT NULL,
    created_at timestamp(6) without time zone NOT NULL,
    updated_at timestamp(6) without time zone NOT NULL
);
CREATE TABLE ctgov.search_terms (
    id bigint NOT NULL,
    term character varying NOT NULL,
    "group" character varying,
    created_at timestamp(6) without time zone NOT NULL,
    updated_at timestamp(6) without time zone NOT NULL
);
CREATE TABLE ctgov.studies (
    nct_id character varying,
    nlm_download_date_description character varying,
    study_first_submitted_date date,
    results_first_submitted_date date,
    disposition_first_submitted_date date,
    last_update_submitted_date date,
    study_first_submitted_qc_date date,
    study_first_posted_date date,
    study_first_posted_date_type character varying,
    results_first_submitted_qc_date date,
    results_first_posted_date date,
    results_first_posted_date_type character varying,
    disposition_first_submitted_qc_date date,
    disposition_first_posted_date date,
    disposition_first_posted_date_type character varying,
    last_update_submitted_qc_date date,
    last_update_posted_date date,
    last_update_posted_date_type character varying,
    start_month_year character varying,
    start_date_type character varying,
    start_date date,
    verification_month_year character varying,
    verification_date date,
    completion_month_year character varying,
    completion_date_type character varying,
    completion_date date,
    primary_completion_month_year character varying,
    primary_completion_date_type character varying,
    primary_completion_date date,
    target_duration character varying,
    study_type character varying,
    acronym character varying,
    baseline_population text,
    brief_title text,
    official_title text,
    overall_status character varying,
    last_known_status character varying,
    phase character varying,
    enrollment integer,
    enrollment_type character varying,
    source character varying,
    limitations_and_caveats character varying,
    number_of_arms integer,
    number_of_groups integer,
    why_stopped character varying,
    has_expanded_access boolean,
    expanded_access_type_individual boolean,
    expanded_access_type_intermediate boolean,
    expanded_access_type_treatment boolean,
    has_dmc boolean,
    is_fda_regulated_drug boolean,
    is_fda_regulated_device boolean,
    is_unapproved_device boolean,
    is_ppsd boolean,
    is_us_export boolean,
    biospec_retention character varying,
    biospec_description text,
    ipd_time_frame character varying,
    ipd_access_criteria character varying,
    ipd_url character varying,
    plan_to_share_ipd character varying,
    plan_to_share_ipd_description character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    source_class character varying,
    delayed_posting boolean,
    expanded_access_nctid character varying,
    expanded_access_status_for_nctid character varying,
    fdaaa801_violation boolean,
    baseline_type_units_analyzed character varying,
    patient_registry boolean
);
CREATE TABLE ctgov.study_references (
    id integer NOT NULL,
    nct_id character varying,
    pmid character varying,
    reference_type character varying,
    citation text
);
CREATE TABLE ctgov.study_searches (
    id integer NOT NULL,
    save_tsv boolean DEFAULT false NOT NULL,
    query character varying NOT NULL,
    "grouping" character varying DEFAULT ''::character varying NOT NULL,
    name character varying DEFAULT ''::character varying NOT NULL,
    beta_api boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    active boolean
);
ALTER TABLE ONLY ctgov.baseline_counts ALTER COLUMN id SET DEFAULT nextval('ctgov.baseline_counts_id_seq'::regclass);
ALTER TABLE ONLY ctgov.baseline_measurements ALTER COLUMN id SET DEFAULT nextval('ctgov.baseline_measurements_id_seq'::regclass);
ALTER TABLE ONLY ctgov.brief_summaries ALTER COLUMN id SET DEFAULT nextval('ctgov.brief_summaries_id_seq'::regclass);
ALTER TABLE ONLY ctgov.browse_conditions ALTER COLUMN id SET DEFAULT nextval('ctgov.browse_conditions_id_seq'::regclass);
ALTER TABLE ONLY ctgov.browse_interventions ALTER COLUMN id SET DEFAULT nextval('ctgov.browse_interventions_id_seq'::regclass);
ALTER TABLE ONLY ctgov.calculated_values ALTER COLUMN id SET DEFAULT nextval('ctgov.calculated_values_id_seq'::regclass);
ALTER TABLE ONLY ctgov.central_contacts ALTER COLUMN id SET DEFAULT nextval('ctgov.central_contacts_id_seq'::regclass);
ALTER TABLE ONLY ctgov.conditions ALTER COLUMN id SET DEFAULT nextval('ctgov.conditions_id_seq'::regclass);
ALTER TABLE ONLY ctgov.countries ALTER COLUMN id SET DEFAULT nextval('ctgov.countries_id_seq'::regclass);
ALTER TABLE ONLY ctgov.design_group_interventions ALTER COLUMN id SET DEFAULT nextval('ctgov.design_group_interventions_id_seq'::regclass);
ALTER TABLE ONLY ctgov.design_groups ALTER COLUMN id SET DEFAULT nextval('ctgov.design_groups_id_seq'::regclass);
ALTER TABLE ONLY ctgov.design_outcomes ALTER COLUMN id SET DEFAULT nextval('ctgov.design_outcomes_id_seq'::regclass);
ALTER TABLE ONLY ctgov.designs ALTER COLUMN id SET DEFAULT nextval('ctgov.designs_id_seq'::regclass);
ALTER TABLE ONLY ctgov.detailed_descriptions ALTER COLUMN id SET DEFAULT nextval('ctgov.detailed_descriptions_id_seq'::regclass);
ALTER TABLE ONLY ctgov.documents ALTER COLUMN id SET DEFAULT nextval('ctgov.documents_id_seq'::regclass);
ALTER TABLE ONLY ctgov.drop_withdrawals ALTER COLUMN id SET DEFAULT nextval('ctgov.drop_withdrawals_id_seq'::regclass);
ALTER TABLE ONLY ctgov.eligibilities ALTER COLUMN id SET DEFAULT nextval('ctgov.eligibilities_id_seq'::regclass);
ALTER TABLE ONLY ctgov.facilities ALTER COLUMN id SET DEFAULT nextval('ctgov.facilities_id_seq'::regclass);
ALTER TABLE ONLY ctgov.facility_contacts ALTER COLUMN id SET DEFAULT nextval('ctgov.facility_contacts_id_seq'::regclass);
ALTER TABLE ONLY ctgov.facility_investigators ALTER COLUMN id SET DEFAULT nextval('ctgov.facility_investigators_id_seq'::regclass);
ALTER TABLE ONLY ctgov.id_information ALTER COLUMN id SET DEFAULT nextval('ctgov.id_information_id_seq'::regclass);
ALTER TABLE ONLY ctgov.intervention_other_names ALTER COLUMN id SET DEFAULT nextval('ctgov.intervention_other_names_id_seq'::regclass);
ALTER TABLE ONLY ctgov.interventions ALTER COLUMN id SET DEFAULT nextval('ctgov.interventions_id_seq'::regclass);
ALTER TABLE ONLY ctgov.ipd_information_types ALTER COLUMN id SET DEFAULT nextval('ctgov.ipd_information_types_id_seq'::regclass);
ALTER TABLE ONLY ctgov.keywords ALTER COLUMN id SET DEFAULT nextval('ctgov.keywords_id_seq'::regclass);
ALTER TABLE ONLY ctgov.links ALTER COLUMN id SET DEFAULT nextval('ctgov.links_id_seq'::regclass);
ALTER TABLE ONLY ctgov.mesh_headings ALTER COLUMN id SET DEFAULT nextval('ctgov.mesh_headings_id_seq'::regclass);
ALTER TABLE ONLY ctgov.mesh_terms ALTER COLUMN id SET DEFAULT nextval('ctgov.mesh_terms_id_seq'::regclass);
ALTER TABLE ONLY ctgov.milestones ALTER COLUMN id SET DEFAULT nextval('ctgov.milestones_id_seq'::regclass);
ALTER TABLE ONLY ctgov.outcome_analyses ALTER COLUMN id SET DEFAULT nextval('ctgov.outcome_analyses_id_seq'::regclass);
ALTER TABLE ONLY ctgov.outcome_analysis_groups ALTER COLUMN id SET DEFAULT nextval('ctgov.outcome_analysis_groups_id_seq'::regclass);
ALTER TABLE ONLY ctgov.outcome_counts ALTER COLUMN id SET DEFAULT nextval('ctgov.outcome_counts_id_seq'::regclass);
ALTER TABLE ONLY ctgov.outcome_measurements ALTER COLUMN id SET DEFAULT nextval('ctgov.outcome_measurements_id_seq'::regclass);
ALTER TABLE ONLY ctgov.outcomes ALTER COLUMN id SET DEFAULT nextval('ctgov.outcomes_id_seq'::regclass);
ALTER TABLE ONLY ctgov.overall_officials ALTER COLUMN id SET DEFAULT nextval('ctgov.overall_officials_id_seq'::regclass);
ALTER TABLE ONLY ctgov.participant_flows ALTER COLUMN id SET DEFAULT nextval('ctgov.participant_flows_id_seq'::regclass);
ALTER TABLE ONLY ctgov.pending_results ALTER COLUMN id SET DEFAULT nextval('ctgov.pending_results_id_seq'::regclass);
ALTER TABLE ONLY ctgov.provided_documents ALTER COLUMN id SET DEFAULT nextval('ctgov.provided_documents_id_seq'::regclass);
ALTER TABLE ONLY ctgov.reported_event_totals ALTER COLUMN id SET DEFAULT nextval('ctgov.reported_event_totals_id_seq'::regclass);
ALTER TABLE ONLY ctgov.reported_events ALTER COLUMN id SET DEFAULT nextval('ctgov.reported_events_id_seq'::regclass);
ALTER TABLE ONLY ctgov.responsible_parties ALTER COLUMN id SET DEFAULT nextval('ctgov.responsible_parties_id_seq'::regclass);
ALTER TABLE ONLY ctgov.result_agreements ALTER COLUMN id SET DEFAULT nextval('ctgov.result_agreements_id_seq'::regclass);
ALTER TABLE ONLY ctgov.result_contacts ALTER COLUMN id SET DEFAULT nextval('ctgov.result_contacts_id_seq'::regclass);
ALTER TABLE ONLY ctgov.result_groups ALTER COLUMN id SET DEFAULT nextval('ctgov.result_groups_id_seq'::regclass);
ALTER TABLE ONLY ctgov.retractions ALTER COLUMN id SET DEFAULT nextval('ctgov.retractions_id_seq'::regclass);
ALTER TABLE ONLY ctgov.search_results ALTER COLUMN id SET DEFAULT nextval('ctgov.search_results_id_seq'::regclass);
ALTER TABLE ONLY ctgov.search_term_results ALTER COLUMN id SET DEFAULT nextval('ctgov.search_term_results_id_seq'::regclass);
ALTER TABLE ONLY ctgov.search_terms ALTER COLUMN id SET DEFAULT nextval('ctgov.search_terms_id_seq'::regclass);
ALTER TABLE ONLY ctgov.sponsors ALTER COLUMN id SET DEFAULT nextval('ctgov.sponsors_id_seq'::regclass);
ALTER TABLE ONLY ctgov.study_references ALTER COLUMN id SET DEFAULT nextval('ctgov.study_references_id_seq'::regclass);
ALTER TABLE ONLY ctgov.study_searches ALTER COLUMN id SET DEFAULT nextval('ctgov.study_searches_id_seq'::regclass);
ALTER TABLE ONLY ctgov.baseline_counts
    ADD CONSTRAINT baseline_counts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.baseline_measurements
    ADD CONSTRAINT baseline_measurements_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.brief_summaries
    ADD CONSTRAINT brief_summaries_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.browse_conditions
    ADD CONSTRAINT browse_conditions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.browse_interventions
    ADD CONSTRAINT browse_interventions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.calculated_values
    ADD CONSTRAINT calculated_values_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.central_contacts
    ADD CONSTRAINT central_contacts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.conditions
    ADD CONSTRAINT conditions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.countries
    ADD CONSTRAINT countries_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.design_group_interventions
    ADD CONSTRAINT design_group_interventions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.design_groups
    ADD CONSTRAINT design_groups_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.design_outcomes
    ADD CONSTRAINT design_outcomes_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.designs
    ADD CONSTRAINT designs_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.detailed_descriptions
    ADD CONSTRAINT detailed_descriptions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.drop_withdrawals
    ADD CONSTRAINT drop_withdrawals_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.eligibilities
    ADD CONSTRAINT eligibilities_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.facilities
    ADD CONSTRAINT facilities_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.facility_contacts
    ADD CONSTRAINT facility_contacts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.facility_investigators
    ADD CONSTRAINT facility_investigators_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.id_information
    ADD CONSTRAINT id_information_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.intervention_other_names
    ADD CONSTRAINT intervention_other_names_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.interventions
    ADD CONSTRAINT interventions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.ipd_information_types
    ADD CONSTRAINT ipd_information_types_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.keywords
    ADD CONSTRAINT keywords_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.links
    ADD CONSTRAINT links_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.mesh_headings
    ADD CONSTRAINT mesh_headings_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.mesh_terms
    ADD CONSTRAINT mesh_terms_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.milestones
    ADD CONSTRAINT milestones_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.outcome_analyses
    ADD CONSTRAINT outcome_analyses_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.outcome_analysis_groups
    ADD CONSTRAINT outcome_analysis_groups_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.outcome_counts
    ADD CONSTRAINT outcome_counts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.outcome_measurements
    ADD CONSTRAINT outcome_measurements_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.outcomes
    ADD CONSTRAINT outcomes_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.overall_officials
    ADD CONSTRAINT overall_officials_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.participant_flows
    ADD CONSTRAINT participant_flows_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.pending_results
    ADD CONSTRAINT pending_results_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.provided_documents
    ADD CONSTRAINT provided_documents_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.reported_event_totals
    ADD CONSTRAINT reported_event_totals_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.reported_events
    ADD CONSTRAINT reported_events_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.responsible_parties
    ADD CONSTRAINT responsible_parties_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.result_agreements
    ADD CONSTRAINT result_agreements_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.result_contacts
    ADD CONSTRAINT result_contacts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.result_groups
    ADD CONSTRAINT result_groups_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.retractions
    ADD CONSTRAINT retractions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.search_results
    ADD CONSTRAINT search_results_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.search_term_results
    ADD CONSTRAINT search_term_results_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.search_terms
    ADD CONSTRAINT search_terms_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.sponsors
    ADD CONSTRAINT sponsors_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.study_references
    ADD CONSTRAINT study_references_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.study_searches
    ADD CONSTRAINT study_searches_pkey PRIMARY KEY (id);
ALTER TABLE ONLY ctgov.baseline_counts
    ADD CONSTRAINT baseline_counts_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.baseline_counts
    ADD CONSTRAINT baseline_counts_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.baseline_measurements
    ADD CONSTRAINT baseline_measurements_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.baseline_measurements
    ADD CONSTRAINT baseline_measurements_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.brief_summaries
    ADD CONSTRAINT brief_summaries_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.browse_conditions
    ADD CONSTRAINT browse_conditions_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.browse_interventions
    ADD CONSTRAINT browse_interventions_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.calculated_values
    ADD CONSTRAINT calculated_values_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.central_contacts
    ADD CONSTRAINT central_contacts_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.conditions
    ADD CONSTRAINT conditions_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.countries
    ADD CONSTRAINT countries_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.design_group_interventions
    ADD CONSTRAINT design_group_interventions_design_group_id_fkey FOREIGN KEY (design_group_id) REFERENCES ctgov.design_groups(id);
ALTER TABLE ONLY ctgov.design_group_interventions
    ADD CONSTRAINT design_group_interventions_intervention_id_fkey FOREIGN KEY (intervention_id) REFERENCES ctgov.interventions(id);
ALTER TABLE ONLY ctgov.design_group_interventions
    ADD CONSTRAINT design_group_interventions_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.design_groups
    ADD CONSTRAINT design_groups_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.design_outcomes
    ADD CONSTRAINT design_outcomes_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.designs
    ADD CONSTRAINT designs_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.detailed_descriptions
    ADD CONSTRAINT detailed_descriptions_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.documents
    ADD CONSTRAINT documents_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.drop_withdrawals
    ADD CONSTRAINT drop_withdrawals_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.drop_withdrawals
    ADD CONSTRAINT drop_withdrawals_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.eligibilities
    ADD CONSTRAINT eligibilities_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.facilities
    ADD CONSTRAINT facilities_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.facility_contacts
    ADD CONSTRAINT facility_contacts_facility_id_fkey FOREIGN KEY (facility_id) REFERENCES ctgov.facilities(id);
ALTER TABLE ONLY ctgov.facility_contacts
    ADD CONSTRAINT facility_contacts_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.facility_investigators
    ADD CONSTRAINT facility_investigators_facility_id_fkey FOREIGN KEY (facility_id) REFERENCES ctgov.facilities(id);
ALTER TABLE ONLY ctgov.facility_investigators
    ADD CONSTRAINT facility_investigators_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.search_term_results
    ADD CONSTRAINT fk_rails_079d8b7607 FOREIGN KEY (search_term_id) REFERENCES ctgov.search_terms(id);
ALTER TABLE ONLY ctgov.id_information
    ADD CONSTRAINT id_information_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.intervention_other_names
    ADD CONSTRAINT intervention_other_names_intervention_id_fkey FOREIGN KEY (intervention_id) REFERENCES ctgov.interventions(id);
ALTER TABLE ONLY ctgov.intervention_other_names
    ADD CONSTRAINT intervention_other_names_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.interventions
    ADD CONSTRAINT interventions_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.ipd_information_types
    ADD CONSTRAINT ipd_information_types_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.keywords
    ADD CONSTRAINT keywords_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.links
    ADD CONSTRAINT links_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.milestones
    ADD CONSTRAINT milestones_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.milestones
    ADD CONSTRAINT milestones_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.outcome_analyses
    ADD CONSTRAINT outcome_analyses_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.outcome_analyses
    ADD CONSTRAINT outcome_analyses_outcome_id_fkey FOREIGN KEY (outcome_id) REFERENCES ctgov.outcomes(id);
ALTER TABLE ONLY ctgov.outcome_analysis_groups
    ADD CONSTRAINT outcome_analysis_groups_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.outcome_analysis_groups
    ADD CONSTRAINT outcome_analysis_groups_outcome_analysis_id_fkey FOREIGN KEY (outcome_analysis_id) REFERENCES ctgov.outcome_analyses(id);
ALTER TABLE ONLY ctgov.outcome_analysis_groups
    ADD CONSTRAINT outcome_analysis_groups_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.outcome_counts
    ADD CONSTRAINT outcome_counts_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.outcome_counts
    ADD CONSTRAINT outcome_counts_outcome_id_fkey FOREIGN KEY (outcome_id) REFERENCES ctgov.outcomes(id);
ALTER TABLE ONLY ctgov.outcome_counts
    ADD CONSTRAINT outcome_counts_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.outcome_measurements
    ADD CONSTRAINT outcome_measurements_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.outcome_measurements
    ADD CONSTRAINT outcome_measurements_outcome_id_fkey FOREIGN KEY (outcome_id) REFERENCES ctgov.outcomes(id);
ALTER TABLE ONLY ctgov.outcome_measurements
    ADD CONSTRAINT outcome_measurements_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.outcomes
    ADD CONSTRAINT outcomes_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.overall_officials
    ADD CONSTRAINT overall_officials_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.participant_flows
    ADD CONSTRAINT participant_flows_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.pending_results
    ADD CONSTRAINT pending_results_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.provided_documents
    ADD CONSTRAINT provided_documents_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.reported_event_totals
    ADD CONSTRAINT reported_event_totals_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.reported_events
    ADD CONSTRAINT reported_events_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.reported_events
    ADD CONSTRAINT reported_events_result_group_id_fkey FOREIGN KEY (result_group_id) REFERENCES ctgov.result_groups(id);
ALTER TABLE ONLY ctgov.responsible_parties
    ADD CONSTRAINT responsible_parties_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.result_agreements
    ADD CONSTRAINT result_agreements_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.result_contacts
    ADD CONSTRAINT result_contacts_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.result_groups
    ADD CONSTRAINT result_groups_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.result_groups
    ADD CONSTRAINT result_groups_outcome_id_fkey FOREIGN KEY (outcome_id) REFERENCES ctgov.outcomes(id);
ALTER TABLE ONLY ctgov.retractions
    ADD CONSTRAINT retractions_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.search_results
    ADD CONSTRAINT search_results_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.sponsors
    ADD CONSTRAINT sponsors_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.studies
    ADD CONSTRAINT studies_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);
ALTER TABLE ONLY ctgov.study_references
    ADD CONSTRAINT study_references_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES ctgov.studies(nct_id);