--
-- PostgreSQL database dump
--

\restrict a2SvsagNLhzQmJk7vWaCEGyqa0raRkSOO2mrThEo82RPSS8rEWSYXYbzD2O6IHM

-- Dumped from database version 14.22 (Ubuntu 14.22-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.22 (Ubuntu 14.22-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: active_operations; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.active_operations (
    operation_id integer NOT NULL,
    user_id integer NOT NULL,
    session_id character varying(36),
    username character varying(50) NOT NULL,
    tool_name character varying(50) NOT NULL,
    function_name character varying(100) NOT NULL,
    operation_name character varying(200) NOT NULL,
    status character varying(20),
    progress_percentage double precision,
    current_step character varying(200),
    total_steps integer,
    completed_steps integer,
    started_at timestamp without time zone,
    updated_at timestamp without time zone,
    completed_at timestamp without time zone,
    estimated_completion timestamp without time zone,
    file_info jsonb,
    parameters jsonb,
    error_message text,
    output_dir character varying(500),
    output_files jsonb
);


ALTER TABLE public.active_operations OWNER TO localization_admin;

--
-- Name: active_operations_operation_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.active_operations_operation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.active_operations_operation_id_seq OWNER TO localization_admin;

--
-- Name: active_operations_operation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.active_operations_operation_id_seq OWNED BY public.active_operations.operation_id;


--
-- Name: announcements; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.announcements (
    announcement_id integer NOT NULL,
    title character varying(100) NOT NULL,
    message text NOT NULL,
    priority character varying(20),
    created_at timestamp without time zone,
    expires_at timestamp without time zone,
    is_active boolean,
    target_users jsonb
);


ALTER TABLE public.announcements OWNER TO localization_admin;

--
-- Name: announcements_announcement_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.announcements_announcement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.announcements_announcement_id_seq OWNER TO localization_admin;

--
-- Name: announcements_announcement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.announcements_announcement_id_seq OWNED BY public.announcements.announcement_id;


--
-- Name: app_versions; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.app_versions (
    version_id integer NOT NULL,
    version_number character varying(20) NOT NULL,
    release_date timestamp without time zone,
    is_latest boolean,
    is_required boolean,
    release_notes text,
    download_url character varying(255)
);


ALTER TABLE public.app_versions OWNER TO localization_admin;

--
-- Name: app_versions_version_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.app_versions_version_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.app_versions_version_id_seq OWNER TO localization_admin;

--
-- Name: app_versions_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.app_versions_version_id_seq OWNED BY public.app_versions.version_id;


--
-- Name: error_logs; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.error_logs (
    error_id integer NOT NULL,
    "timestamp" timestamp without time zone,
    user_id integer,
    machine_id character varying(64) NOT NULL,
    tool_name character varying(50) NOT NULL,
    function_name character varying(100) NOT NULL,
    error_type character varying(100) NOT NULL,
    error_message text NOT NULL,
    stack_trace text,
    app_version character varying(20) NOT NULL,
    context jsonb
);


ALTER TABLE public.error_logs OWNER TO localization_admin;

--
-- Name: error_logs_error_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.error_logs_error_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.error_logs_error_id_seq OWNER TO localization_admin;

--
-- Name: error_logs_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.error_logs_error_id_seq OWNED BY public.error_logs.error_id;


--
-- Name: function_usage_stats; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.function_usage_stats (
    stat_id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    tool_name character varying(50) NOT NULL,
    function_name character varying(100) NOT NULL,
    total_uses integer,
    unique_users integer,
    total_duration_seconds double precision,
    avg_duration_seconds double precision,
    min_duration_seconds double precision,
    max_duration_seconds double precision
);


ALTER TABLE public.function_usage_stats OWNER TO localization_admin;

--
-- Name: function_usage_stats_stat_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.function_usage_stats_stat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.function_usage_stats_stat_id_seq OWNER TO localization_admin;

--
-- Name: function_usage_stats_stat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.function_usage_stats_stat_id_seq OWNED BY public.function_usage_stats.stat_id;


--
-- Name: installations; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.installations (
    installation_id character varying(32) NOT NULL,
    api_key_hash character varying(255) NOT NULL,
    installation_name character varying(100) NOT NULL,
    version character varying(20) NOT NULL,
    owner_email character varying(100),
    is_active boolean,
    created_at timestamp without time zone,
    last_seen timestamp without time zone,
    last_version character varying(20),
    extra_data jsonb
);


ALTER TABLE public.installations OWNER TO localization_admin;

--
-- Name: ldm_active_sessions; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_active_sessions (
    id integer NOT NULL,
    file_id integer NOT NULL,
    user_id integer NOT NULL,
    cursor_row integer,
    editing_row integer,
    joined_at timestamp without time zone,
    last_seen timestamp without time zone
);


ALTER TABLE public.ldm_active_sessions OWNER TO localization_admin;

--
-- Name: ldm_active_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_active_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_active_sessions_id_seq OWNER TO localization_admin;

--
-- Name: ldm_active_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_active_sessions_id_seq OWNED BY public.ldm_active_sessions.id;


--
-- Name: ldm_active_tms; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_active_tms (
    id integer NOT NULL,
    tm_id integer NOT NULL,
    project_id integer,
    file_id integer,
    priority integer,
    activated_by integer,
    activated_at timestamp without time zone
);


ALTER TABLE public.ldm_active_tms OWNER TO localization_admin;

--
-- Name: ldm_active_tms_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_active_tms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_active_tms_id_seq OWNER TO localization_admin;

--
-- Name: ldm_active_tms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_active_tms_id_seq OWNED BY public.ldm_active_tms.id;


--
-- Name: ldm_backups; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_backups (
    id integer NOT NULL,
    backup_type character varying(50) NOT NULL,
    project_id integer,
    file_id integer,
    tm_id integer,
    backup_path character varying(500) NOT NULL,
    file_size bigint,
    status character varying(50),
    error_message text,
    trigger character varying(100),
    created_by integer,
    created_at timestamp without time zone,
    expires_at timestamp without time zone
);


ALTER TABLE public.ldm_backups OWNER TO localization_admin;

--
-- Name: ldm_backups_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_backups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_backups_id_seq OWNER TO localization_admin;

--
-- Name: ldm_backups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_backups_id_seq OWNED BY public.ldm_backups.id;


--
-- Name: ldm_edit_history; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_edit_history (
    id integer NOT NULL,
    row_id integer NOT NULL,
    user_id integer,
    old_target text,
    new_target text,
    old_status character varying(20),
    new_status character varying(20),
    edited_at timestamp without time zone
);


ALTER TABLE public.ldm_edit_history OWNER TO localization_admin;

--
-- Name: ldm_edit_history_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_edit_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_edit_history_id_seq OWNER TO localization_admin;

--
-- Name: ldm_edit_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_edit_history_id_seq OWNED BY public.ldm_edit_history.id;


--
-- Name: ldm_files; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_files (
    id integer NOT NULL,
    project_id integer NOT NULL,
    folder_id integer,
    name character varying(255) NOT NULL,
    original_filename character varying(255) NOT NULL,
    format character varying(20) NOT NULL,
    row_count integer,
    source_language character varying(10),
    target_language character varying(10),
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    created_by integer,
    extra_data jsonb
);


ALTER TABLE public.ldm_files OWNER TO localization_admin;

--
-- Name: ldm_files_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_files_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_files_id_seq OWNER TO localization_admin;

--
-- Name: ldm_files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_files_id_seq OWNED BY public.ldm_files.id;


--
-- Name: ldm_folders; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_folders (
    id integer NOT NULL,
    project_id integer NOT NULL,
    parent_id integer,
    name character varying(200) NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.ldm_folders OWNER TO localization_admin;

--
-- Name: ldm_folders_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_folders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_folders_id_seq OWNER TO localization_admin;

--
-- Name: ldm_folders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_folders_id_seq OWNED BY public.ldm_folders.id;


--
-- Name: ldm_platforms; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_platforms (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    owner_id integer NOT NULL,
    description text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_restricted boolean DEFAULT false
);


ALTER TABLE public.ldm_platforms OWNER TO localization_admin;

--
-- Name: ldm_platforms_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_platforms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_platforms_id_seq OWNER TO localization_admin;

--
-- Name: ldm_platforms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_platforms_id_seq OWNED BY public.ldm_platforms.id;


--
-- Name: ldm_projects; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_projects (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    owner_id integer NOT NULL,
    description text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    platform_id integer,
    is_restricted boolean DEFAULT false
);


ALTER TABLE public.ldm_projects OWNER TO localization_admin;

--
-- Name: ldm_projects_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_projects_id_seq OWNER TO localization_admin;

--
-- Name: ldm_projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_projects_id_seq OWNED BY public.ldm_projects.id;


--
-- Name: ldm_qa_results; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_qa_results (
    id integer NOT NULL,
    row_id integer NOT NULL,
    file_id integer NOT NULL,
    check_type character varying(50) NOT NULL,
    severity character varying(20),
    message text NOT NULL,
    details jsonb,
    created_at timestamp without time zone,
    resolved_at timestamp without time zone,
    resolved_by integer
);


ALTER TABLE public.ldm_qa_results OWNER TO localization_admin;

--
-- Name: ldm_qa_results_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_qa_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_qa_results_id_seq OWNER TO localization_admin;

--
-- Name: ldm_qa_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_qa_results_id_seq OWNED BY public.ldm_qa_results.id;


--
-- Name: ldm_resource_access; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_resource_access (
    id integer NOT NULL,
    platform_id integer,
    project_id integer,
    user_id integer NOT NULL,
    access_level character varying(20),
    granted_by integer,
    granted_at timestamp without time zone
);


ALTER TABLE public.ldm_resource_access OWNER TO localization_admin;

--
-- Name: ldm_resource_access_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_resource_access_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_resource_access_id_seq OWNER TO localization_admin;

--
-- Name: ldm_resource_access_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_resource_access_id_seq OWNED BY public.ldm_resource_access.id;


--
-- Name: ldm_rows; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_rows (
    id integer NOT NULL,
    file_id integer NOT NULL,
    row_num integer NOT NULL,
    string_id character varying(255),
    source text,
    target text,
    status character varying(20),
    updated_by integer,
    updated_at timestamp without time zone,
    extra_data jsonb,
    qa_checked_at timestamp without time zone,
    qa_flag_count integer DEFAULT 0
);


ALTER TABLE public.ldm_rows OWNER TO localization_admin;

--
-- Name: ldm_rows_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_rows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_rows_id_seq OWNER TO localization_admin;

--
-- Name: ldm_rows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_rows_id_seq OWNED BY public.ldm_rows.id;


--
-- Name: ldm_tm_assignments; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_tm_assignments (
    id integer NOT NULL,
    tm_id integer NOT NULL,
    platform_id integer,
    project_id integer,
    folder_id integer,
    is_active boolean NOT NULL,
    priority integer,
    assigned_by integer,
    assigned_at timestamp without time zone,
    activated_at timestamp without time zone
);


ALTER TABLE public.ldm_tm_assignments OWNER TO localization_admin;

--
-- Name: ldm_tm_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_tm_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_tm_assignments_id_seq OWNER TO localization_admin;

--
-- Name: ldm_tm_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_tm_assignments_id_seq OWNED BY public.ldm_tm_assignments.id;


--
-- Name: ldm_tm_entries; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_tm_entries (
    id integer NOT NULL,
    tm_id integer NOT NULL,
    source_text text NOT NULL,
    target_text text,
    source_hash character varying(64) NOT NULL,
    created_by character varying(255),
    change_date timestamp without time zone,
    created_at timestamp without time zone,
    string_id character varying(255),
    updated_at timestamp without time zone,
    is_confirmed boolean DEFAULT false,
    confirmed_at timestamp without time zone,
    confirmed_by character varying(255),
    updated_by character varying(255)
);


ALTER TABLE public.ldm_tm_entries OWNER TO localization_admin;

--
-- Name: ldm_tm_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_tm_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_tm_entries_id_seq OWNER TO localization_admin;

--
-- Name: ldm_tm_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_tm_entries_id_seq OWNED BY public.ldm_tm_entries.id;


--
-- Name: ldm_tm_indexes; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_tm_indexes (
    id integer NOT NULL,
    tm_id integer NOT NULL,
    index_type character varying(50) NOT NULL,
    index_path character varying(500) NOT NULL,
    entry_count integer,
    file_size bigint,
    status character varying(50),
    error_message text,
    created_at timestamp without time zone,
    built_at timestamp without time zone
);


ALTER TABLE public.ldm_tm_indexes OWNER TO localization_admin;

--
-- Name: ldm_tm_indexes_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_tm_indexes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_tm_indexes_id_seq OWNER TO localization_admin;

--
-- Name: ldm_tm_indexes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_tm_indexes_id_seq OWNED BY public.ldm_tm_indexes.id;


--
-- Name: ldm_translation_memories; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_translation_memories (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    owner_id integer NOT NULL,
    source_lang character varying(10),
    target_lang character varying(10),
    entry_count integer,
    whole_pairs integer,
    line_pairs integer,
    status character varying(50),
    error_message text,
    storage_path character varying(500),
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    indexed_at timestamp without time zone,
    mode character varying(20) DEFAULT 'standard'::character varying
);


ALTER TABLE public.ldm_translation_memories OWNER TO localization_admin;

--
-- Name: ldm_translation_memories_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_translation_memories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_translation_memories_id_seq OWNER TO localization_admin;

--
-- Name: ldm_translation_memories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_translation_memories_id_seq OWNED BY public.ldm_translation_memories.id;


--
-- Name: ldm_trash; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.ldm_trash (
    id integer NOT NULL,
    item_type character varying(50) NOT NULL,
    item_id integer NOT NULL,
    item_name character varying(255) NOT NULL,
    parent_project_id integer,
    parent_folder_id integer,
    item_data jsonb NOT NULL,
    deleted_by integer,
    deleted_at timestamp without time zone,
    expires_at timestamp without time zone NOT NULL,
    status character varying(50)
);


ALTER TABLE public.ldm_trash OWNER TO localization_admin;

--
-- Name: ldm_trash_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.ldm_trash_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ldm_trash_id_seq OWNER TO localization_admin;

--
-- Name: ldm_trash_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.ldm_trash_id_seq OWNED BY public.ldm_trash.id;


--
-- Name: log_entries; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.log_entries (
    log_id integer NOT NULL,
    user_id integer NOT NULL,
    session_id character varying(36),
    username character varying(50) NOT NULL,
    machine_id character varying(64) NOT NULL,
    tool_name character varying(50) NOT NULL,
    function_name character varying(100) NOT NULL,
    "timestamp" timestamp without time zone,
    duration_seconds double precision NOT NULL,
    status character varying(20),
    error_message text,
    file_info jsonb,
    parameters jsonb
);


ALTER TABLE public.log_entries OWNER TO localization_admin;

--
-- Name: log_entries_log_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.log_entries_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.log_entries_log_id_seq OWNER TO localization_admin;

--
-- Name: log_entries_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.log_entries_log_id_seq OWNED BY public.log_entries.log_id;


--
-- Name: performance_metrics; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.performance_metrics (
    metric_id integer NOT NULL,
    "timestamp" timestamp without time zone,
    tool_name character varying(50) NOT NULL,
    function_name character varying(100) NOT NULL,
    duration_seconds double precision NOT NULL,
    cpu_usage_percent double precision,
    memory_mb double precision,
    file_size_mb double precision,
    rows_processed integer
);


ALTER TABLE public.performance_metrics OWNER TO localization_admin;

--
-- Name: performance_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.performance_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.performance_metrics_metric_id_seq OWNER TO localization_admin;

--
-- Name: performance_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.performance_metrics_metric_id_seq OWNED BY public.performance_metrics.metric_id;


--
-- Name: remote_logs; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.remote_logs (
    log_id integer NOT NULL,
    installation_id character varying(32) NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    level character varying(20) NOT NULL,
    message text NOT NULL,
    data jsonb,
    source character varying(50) NOT NULL,
    component character varying(100),
    received_at timestamp without time zone
);


ALTER TABLE public.remote_logs OWNER TO localization_admin;

--
-- Name: remote_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.remote_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.remote_logs_log_id_seq OWNER TO localization_admin;

--
-- Name: remote_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.remote_logs_log_id_seq OWNED BY public.remote_logs.log_id;


--
-- Name: remote_sessions; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.remote_sessions (
    session_id character varying(36) NOT NULL,
    installation_id character varying(32) NOT NULL,
    started_at timestamp without time zone,
    ended_at timestamp without time zone,
    last_heartbeat timestamp without time zone,
    duration_seconds integer,
    ip_address character varying(45),
    app_version character varying(20) NOT NULL,
    is_active boolean,
    end_reason character varying(50)
);


ALTER TABLE public.remote_sessions OWNER TO localization_admin;

--
-- Name: sessions; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.sessions (
    session_id character varying(36) NOT NULL,
    user_id integer NOT NULL,
    machine_id character varying(64) NOT NULL,
    ip_address character varying(45),
    app_version character varying(20) NOT NULL,
    session_start timestamp without time zone,
    last_activity timestamp without time zone,
    is_active boolean
);


ALTER TABLE public.sessions OWNER TO localization_admin;

--
-- Name: telemetry_summary; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.telemetry_summary (
    summary_id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    installation_id character varying(32) NOT NULL,
    total_sessions integer,
    total_duration_seconds integer,
    avg_session_seconds double precision,
    tools_used jsonb,
    total_operations integer,
    info_count integer,
    success_count integer,
    warning_count integer,
    error_count integer,
    critical_count integer,
    updated_at timestamp without time zone
);


ALTER TABLE public.telemetry_summary OWNER TO localization_admin;

--
-- Name: telemetry_summary_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.telemetry_summary_summary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.telemetry_summary_summary_id_seq OWNER TO localization_admin;

--
-- Name: telemetry_summary_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.telemetry_summary_summary_id_seq OWNED BY public.telemetry_summary.summary_id;


--
-- Name: tool_usage_stats; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.tool_usage_stats (
    stat_id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    tool_name character varying(50) NOT NULL,
    total_uses integer,
    unique_users integer,
    total_duration_seconds double precision,
    avg_duration_seconds double precision,
    success_count integer,
    error_count integer
);


ALTER TABLE public.tool_usage_stats OWNER TO localization_admin;

--
-- Name: tool_usage_stats_stat_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.tool_usage_stats_stat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tool_usage_stats_stat_id_seq OWNER TO localization_admin;

--
-- Name: tool_usage_stats_stat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.tool_usage_stats_stat_id_seq OWNED BY public.tool_usage_stats.stat_id;


--
-- Name: update_history; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.update_history (
    update_id integer NOT NULL,
    user_id integer NOT NULL,
    from_version character varying(20) NOT NULL,
    to_version character varying(20) NOT NULL,
    update_timestamp timestamp without time zone,
    machine_id character varying(64) NOT NULL
);


ALTER TABLE public.update_history OWNER TO localization_admin;

--
-- Name: update_history_update_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.update_history_update_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.update_history_update_id_seq OWNER TO localization_admin;

--
-- Name: update_history_update_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.update_history_update_id_seq OWNED BY public.update_history.update_id;


--
-- Name: user_activity_summary; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.user_activity_summary (
    summary_id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    total_operations integer,
    total_duration_seconds double precision,
    tools_used jsonb,
    first_activity timestamp without time zone,
    last_activity timestamp without time zone
);


ALTER TABLE public.user_activity_summary OWNER TO localization_admin;

--
-- Name: user_activity_summary_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.user_activity_summary_summary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_activity_summary_summary_id_seq OWNER TO localization_admin;

--
-- Name: user_activity_summary_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.user_activity_summary_summary_id_seq OWNED BY public.user_activity_summary.summary_id;


--
-- Name: user_capabilities; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.user_capabilities (
    id integer NOT NULL,
    user_id integer NOT NULL,
    capability_name character varying(50) NOT NULL,
    granted_by integer,
    granted_at timestamp without time zone,
    expires_at timestamp without time zone
);


ALTER TABLE public.user_capabilities OWNER TO localization_admin;

--
-- Name: user_capabilities_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.user_capabilities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_capabilities_id_seq OWNER TO localization_admin;

--
-- Name: user_capabilities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.user_capabilities_id_seq OWNED BY public.user_capabilities.id;


--
-- Name: user_feedback; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.user_feedback (
    feedback_id integer NOT NULL,
    user_id integer NOT NULL,
    "timestamp" timestamp without time zone,
    feedback_type character varying(20) NOT NULL,
    tool_name character varying(50),
    subject character varying(200) NOT NULL,
    description text NOT NULL,
    rating integer,
    status character varying(20),
    admin_response text
);


ALTER TABLE public.user_feedback OWNER TO localization_admin;

--
-- Name: user_feedback_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.user_feedback_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_feedback_feedback_id_seq OWNER TO localization_admin;

--
-- Name: user_feedback_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.user_feedback_feedback_id_seq OWNED BY public.user_feedback.feedback_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: localization_admin
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    email character varying(100),
    full_name character varying(100),
    department character varying(50),
    team character varying(100),
    language character varying(50),
    role character varying(20),
    is_active boolean,
    created_at timestamp without time zone,
    created_by integer,
    last_login timestamp without time zone,
    last_password_change timestamp without time zone,
    must_change_password boolean
);


ALTER TABLE public.users OWNER TO localization_admin;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: localization_admin
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_user_id_seq OWNER TO localization_admin;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: localization_admin
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: active_operations operation_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.active_operations ALTER COLUMN operation_id SET DEFAULT nextval('public.active_operations_operation_id_seq'::regclass);


--
-- Name: announcements announcement_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.announcements ALTER COLUMN announcement_id SET DEFAULT nextval('public.announcements_announcement_id_seq'::regclass);


--
-- Name: app_versions version_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.app_versions ALTER COLUMN version_id SET DEFAULT nextval('public.app_versions_version_id_seq'::regclass);


--
-- Name: error_logs error_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.error_logs ALTER COLUMN error_id SET DEFAULT nextval('public.error_logs_error_id_seq'::regclass);


--
-- Name: function_usage_stats stat_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.function_usage_stats ALTER COLUMN stat_id SET DEFAULT nextval('public.function_usage_stats_stat_id_seq'::regclass);


--
-- Name: ldm_active_sessions id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_sessions ALTER COLUMN id SET DEFAULT nextval('public.ldm_active_sessions_id_seq'::regclass);


--
-- Name: ldm_active_tms id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_tms ALTER COLUMN id SET DEFAULT nextval('public.ldm_active_tms_id_seq'::regclass);


--
-- Name: ldm_backups id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_backups ALTER COLUMN id SET DEFAULT nextval('public.ldm_backups_id_seq'::regclass);


--
-- Name: ldm_edit_history id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_edit_history ALTER COLUMN id SET DEFAULT nextval('public.ldm_edit_history_id_seq'::regclass);


--
-- Name: ldm_files id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_files ALTER COLUMN id SET DEFAULT nextval('public.ldm_files_id_seq'::regclass);


--
-- Name: ldm_folders id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_folders ALTER COLUMN id SET DEFAULT nextval('public.ldm_folders_id_seq'::regclass);


--
-- Name: ldm_platforms id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_platforms ALTER COLUMN id SET DEFAULT nextval('public.ldm_platforms_id_seq'::regclass);


--
-- Name: ldm_projects id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_projects ALTER COLUMN id SET DEFAULT nextval('public.ldm_projects_id_seq'::regclass);


--
-- Name: ldm_qa_results id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_qa_results ALTER COLUMN id SET DEFAULT nextval('public.ldm_qa_results_id_seq'::regclass);


--
-- Name: ldm_resource_access id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access ALTER COLUMN id SET DEFAULT nextval('public.ldm_resource_access_id_seq'::regclass);


--
-- Name: ldm_rows id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_rows ALTER COLUMN id SET DEFAULT nextval('public.ldm_rows_id_seq'::regclass);


--
-- Name: ldm_tm_assignments id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments ALTER COLUMN id SET DEFAULT nextval('public.ldm_tm_assignments_id_seq'::regclass);


--
-- Name: ldm_tm_entries id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_entries ALTER COLUMN id SET DEFAULT nextval('public.ldm_tm_entries_id_seq'::regclass);


--
-- Name: ldm_tm_indexes id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_indexes ALTER COLUMN id SET DEFAULT nextval('public.ldm_tm_indexes_id_seq'::regclass);


--
-- Name: ldm_translation_memories id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_translation_memories ALTER COLUMN id SET DEFAULT nextval('public.ldm_translation_memories_id_seq'::regclass);


--
-- Name: ldm_trash id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_trash ALTER COLUMN id SET DEFAULT nextval('public.ldm_trash_id_seq'::regclass);


--
-- Name: log_entries log_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.log_entries ALTER COLUMN log_id SET DEFAULT nextval('public.log_entries_log_id_seq'::regclass);


--
-- Name: performance_metrics metric_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.performance_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.performance_metrics_metric_id_seq'::regclass);


--
-- Name: remote_logs log_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.remote_logs ALTER COLUMN log_id SET DEFAULT nextval('public.remote_logs_log_id_seq'::regclass);


--
-- Name: telemetry_summary summary_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.telemetry_summary ALTER COLUMN summary_id SET DEFAULT nextval('public.telemetry_summary_summary_id_seq'::regclass);


--
-- Name: tool_usage_stats stat_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.tool_usage_stats ALTER COLUMN stat_id SET DEFAULT nextval('public.tool_usage_stats_stat_id_seq'::regclass);


--
-- Name: update_history update_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.update_history ALTER COLUMN update_id SET DEFAULT nextval('public.update_history_update_id_seq'::regclass);


--
-- Name: user_activity_summary summary_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_activity_summary ALTER COLUMN summary_id SET DEFAULT nextval('public.user_activity_summary_summary_id_seq'::regclass);


--
-- Name: user_capabilities id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_capabilities ALTER COLUMN id SET DEFAULT nextval('public.user_capabilities_id_seq'::regclass);


--
-- Name: user_feedback feedback_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_feedback ALTER COLUMN feedback_id SET DEFAULT nextval('public.user_feedback_feedback_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Data for Name: active_operations; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.active_operations (operation_id, user_id, session_id, username, tool_name, function_name, operation_name, status, progress_percentage, current_step, total_steps, completed_steps, started_at, updated_at, completed_at, estimated_completion, file_info, parameters, error_message, output_dir, output_files) FROM stdin;
476	2	\N	admin	LDM	upload_file	Upload: api_test_locstr.xml	completed	100	Completed	\N	3	2026-03-15 18:08:49.32014	2026-03-15 18:08:49.422309	2026-03-15 18:08:49.422307	\N	\N	{"filename": "api_test_locstr.xml", "row_count": 3}	\N	\N	\N
229	1	\N	system	LDM	auto_sync_tm	Auto-sync TM: Main TM	completed	100	Completed	\N	\N	2026-01-03 08:15:44.360746	2026-01-03 08:15:57.988314	2026-01-03 08:15:57.988313	\N	\N	{"tm_id": 1, "tm_name": "Main TM"}	\N	\N	\N
470	2	\N	admin	LDM	upload_file	Upload: test_api.loc.xml	completed	100	Completed	\N	3	2026-03-15 18:03:52.284766	2026-03-15 18:03:52.401248	2026-03-15 18:03:52.401246	\N	\N	{"filename": "test_api.loc.xml", "row_count": 3}	\N	\N	\N
128	494	\N	inlinetest	LDM	upload_file	Upload: sample_language_data.txt	completed	100	Completed	\N	63	2025-12-28 15:24:52.04249	2025-12-28 15:24:52.191873	2025-12-28 15:24:52.191871	\N	\N	{"filename": "sample_language_data.txt", "row_count": 63}	\N	\N	\N
230	1	\N	system	LDM	auto_sync_tm	Auto-sync TM: Main TM	completed	100	Completed	\N	\N	2026-01-03 08:15:58.069177	2026-01-03 08:15:58.192779	2026-01-03 08:15:58.192778	\N	\N	{"tm_id": 1, "tm_name": "Main TM"}	\N	\N	\N
571	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 02:44:56.698126	2026-03-16 02:44:57.036523	2026-03-16 02:44:57.03652	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
567	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 02:44:54.66452	2026-03-16 02:44:54.954016	2026-03-16 02:44:54.954014	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
231	1	\N	system	LDM	auto_sync_tm	Auto-sync TM: Main TM	completed	100	Completed	\N	\N	2026-01-03 08:15:58.254945	2026-01-03 08:15:58.349501	2026-01-03 08:15:58.349501	\N	\N	{"tm_id": 1, "tm_name": "Main TM"}	\N	\N	\N
611	2	\N	admin	LDM	upload_tm	Upload TM: E2E-CRUD-Delete	failed	30	Inserting entries...	\N	\N	2026-03-16 17:55:18.160077	2026-03-16 17:55:18.241525	2026-03-16 17:55:18.241524	\N	\N	{"mode": "standard", "name": "E2E-CRUD-Delete", "filename": "ephemeral.txt"}	ValueError: No valid entries found in file	\N	\N
471	2	\N	admin	LDM	upload_file	Upload: api_test_locstr.xml	completed	100	Completed	\N	3	2026-03-15 18:06:41.97035	2026-03-15 18:06:42.064255	2026-03-15 18:06:42.064252	\N	\N	{"filename": "api_test_locstr.xml", "row_count": 3}	\N	\N	\N
605	2	\N	admin	LDM	upload_tm	Upload TM: IntWf-Pretranslate-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:54:49.718423	2026-03-16 17:54:49.799624	2026-03-16 17:54:49.799623	\N	\N	{"mode": "standard", "name": "IntWf-Pretranslate-TM", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
486	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:10:30.335959	2026-03-16 01:10:30.41874	2026-03-16 01:10:30.418739	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
472	2	\N	admin	LDM	upload_file	Upload: api_test_locstr.xml	completed	100	Completed	\N	3	2026-03-15 18:07:22.093695	2026-03-15 18:07:22.209964	2026-03-15 18:07:22.209963	\N	\N	{"filename": "api_test_locstr.xml", "row_count": 3}	\N	\N	\N
232	1	\N	testuser	LDM	build_tm_indexes	Build TM Indexes: <MagicMock name='mock.scalar_one_or_none().name' id='140685781088624'>	completed	100	Completed	4	4	2026-01-03 08:15:59.794373	2026-01-03 08:16:00.212093	2026-01-03 08:16:00.212092	\N	\N	{"tm_id": 1}	\N	\N	\N
568	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 02:44:55.191387	2026-03-16 02:44:55.494681	2026-03-16 02:44:55.494679	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
608	2	\N	admin	LDM	upload_tm	Upload TM: Korean-TMSearch	failed	30	Inserting entries...	\N	\N	2026-03-16 17:54:58.642367	2026-03-16 17:54:57.229036	2026-03-16 17:54:57.229035	\N	\N	{"mode": "standard", "name": "Korean-TMSearch", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
473	2	\N	admin	LDM	upload_file	Upload: api_test_locstr.xml	completed	100	Completed	\N	3	2026-03-15 18:08:03.943223	2026-03-15 18:08:04.041487	2026-03-15 18:08:04.041485	\N	\N	{"filename": "api_test_locstr.xml", "row_count": 3}	\N	\N	\N
606	2	\N	admin	LDM	upload_file	Upload: kr_up.xlsx	completed	100	Completed	\N	2	2026-03-16 17:54:56.541534	2026-03-16 17:54:56.674807	2026-03-16 17:54:56.674805	\N	\N	{"filename": "kr_up.xlsx", "row_count": 2}	\N	\N	\N
487	2	\N	admin	LDM	upload_file	Upload: test_br.xml	completed	100	Completed	\N	1	2026-03-16 01:11:08.592035	2026-03-16 01:11:08.680282	2026-03-16 01:11:08.680281	\N	\N	{"filename": "test_br.xml", "row_count": 1}	\N	\N	\N
569	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 02:44:55.648174	2026-03-16 02:44:55.946965	2026-03-16 02:44:55.946963	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
474	2	\N	admin	LDM	upload_file	Upload: api_test_locstr.xml	completed	100	Completed	\N	3	2026-03-15 18:08:13.294709	2026-03-15 18:08:13.409695	2026-03-15 18:08:13.409693	\N	\N	{"filename": "api_test_locstr.xml", "row_count": 3}	\N	\N	\N
610	2	\N	admin	LDM	upload_tm	Upload TM: E2E-CRUD-Create	failed	30	Inserting entries...	\N	\N	2026-03-16 17:55:17.942654	2026-03-16 17:55:18.031874	2026-03-16 17:55:18.031873	\N	\N	{"mode": "standard", "name": "E2E-CRUD-Create", "filename": "crud.txt"}	ValueError: No valid entries found in file	\N	\N
475	2	\N	admin	LDM	upload_file	Upload: api_test_locstr.xml	completed	100	Completed	\N	3	2026-03-15 18:08:40.953251	2026-03-15 18:08:41.050648	2026-03-15 18:08:41.050646	\N	\N	{"filename": "api_test_locstr.xml", "row_count": 3}	\N	\N	\N
570	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 02:44:56.114066	2026-03-16 02:44:56.378481	2026-03-16 02:44:56.37848	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
607	2	\N	admin	LDM	upload_tm	Upload TM: Korean-TXT-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:54:56.889149	2026-03-16 17:54:56.971104	2026-03-16 17:54:56.971104	\N	\N	{"mode": "standard", "name": "Korean-TXT-TM", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
609	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Test-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:54:59.476385	2026-03-16 17:54:59.561579	2026-03-16 17:54:59.561578	\N	\N	{"mode": "standard", "name": "E2E-Test-TM", "filename": "test_tm.txt"}	ValueError: No valid entries found in file	\N	\N
612	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Upload-TXT	failed	30	Inserting entries...	\N	\N	2026-03-16 17:55:18.538676	2026-03-16 17:55:18.634706	2026-03-16 17:55:18.634705	\N	\N	{"mode": "standard", "name": "E2E-Upload-TXT", "filename": "test.txt"}	ValueError: No valid entries found in file	\N	\N
613	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Upload-BrTag	failed	30	Inserting entries...	\N	\N	2026-03-16 17:55:18.758166	2026-03-16 17:55:18.835839	2026-03-16 17:55:18.835839	\N	\N	{"mode": "standard", "name": "E2E-Upload-BrTag", "filename": "brtag.txt"}	ValueError: No valid entries found in file	\N	\N
614	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Upload-Count	failed	30	Inserting entries...	\N	\N	2026-03-16 17:55:18.910066	2026-03-16 17:55:18.992825	2026-03-16 17:55:18.992824	\N	\N	{"mode": "standard", "name": "E2E-Upload-Count", "filename": "count.txt"}	ValueError: No valid entries found in file	\N	\N
40	157	\N	ldm_test_user	LDM	upload_tm	Upload TM: Test TM Upload	failed	30	Inserting entries...	\N	\N	2025-12-22 02:36:59.227558	2025-12-22 02:36:59.371466	2025-12-22 02:36:59.371465	\N	\N	{"mode": "standard", "name": "Test TM Upload", "filename": "test.xlsx"}	BadZipFile: File is not a zip file	\N	\N
233	1	\N	system	LDM	auto_sync_tm	Auto-sync TM: Main TM	completed	100	Completed	\N	\N	2026-01-03 08:18:29.346509	2026-01-03 08:18:33.804449	2026-01-03 08:18:33.804448	\N	\N	{"tm_id": 1, "tm_name": "Main TM"}	\N	\N	\N
572	2	\N	admin	LDM	upload_file	Upload: test.xml	completed	100	Completed	\N	1	2026-03-16 04:07:11.019705	2026-03-16 04:07:11.208977	2026-03-16 04:07:11.208975	\N	\N	{"filename": "test.xml", "row_count": 1}	\N	\N	\N
234	1	\N	system	LDM	auto_sync_tm	Auto-sync TM: Main TM	completed	100	Completed	\N	\N	2026-01-03 08:18:33.889304	2026-01-03 08:18:33.983065	2026-01-03 08:18:33.983064	\N	\N	{"tm_id": 1, "tm_name": "Main TM"}	\N	\N	\N
447	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:00:34.960496	2026-03-14 11:00:35.673288	2026-03-14 11:00:35.673286	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
235	1	\N	system	LDM	auto_sync_tm	Auto-sync TM: Main TM	completed	100	Completed	\N	\N	2026-01-03 08:18:34.04733	2026-01-03 08:18:34.161431	2026-01-03 08:18:34.161431	\N	\N	{"tm_id": 1, "tm_name": "Main TM"}	\N	\N	\N
193	1	\N	dev_admin	LDM	upload_file	Upload: simple_test.txt	completed	100	Completed	\N	10	2025-12-30 16:29:43.322032	2025-12-30 16:29:43.503912	2025-12-30 16:29:43.503911	\N	\N	{"filename": "simple_test.txt", "row_count": 10}	\N	\N	\N
573	2	\N	admin	LDM	upload_file	Upload: demo.xml	completed	100	Completed	\N	1	2026-03-16 04:08:36.908345	2026-03-16 04:08:37.002419	2026-03-16 04:08:37.002418	\N	\N	{"filename": "demo.xml", "row_count": 1}	\N	\N	\N
448	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:00:50.686694	2026-03-14 11:00:51.300606	2026-03-14 11:00:51.300605	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
451	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:00:51.188521	2026-03-14 11:00:51.671756	2026-03-14 11:00:51.671752	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
453	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:01:42.143603	2026-03-14 11:01:42.414891	2026-03-14 11:01:42.414889	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
236	1	\N	dev_admin	LDM	upload_file	Upload: sample_language_data.txt	completed	100	Completed	\N	63	2026-01-03 12:01:07.346992	2026-01-03 12:01:07.452187	2026-01-03 12:01:07.452185	\N	\N	{"filename": "sample_language_data.txt", "row_count": 63}	\N	\N	\N
449	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:00:50.788661	2026-03-14 11:00:51.465579	2026-03-14 11:00:51.465578	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
327	1	\N	testuser	LDM	upload_tm	Upload TM: Test TM	failed	30	Inserting entries...	\N	\N	2026-01-11 10:14:39.182851	2026-01-11 10:14:39.33662	2026-01-11 10:14:39.336619	\N	\N	{"mode": "standard", "name": "Test TM", "filename": "test.txt"}	ValueError: No valid entries found in file	\N	\N
574	2	\N	admin	LDM	upload_file	Upload: locstr_kor.xml	completed	100	Completed	\N	8	2026-03-16 05:05:28.067037	2026-03-16 05:05:28.169946	2026-03-16 05:05:28.169944	\N	\N	{"filename": "locstr_kor.xml", "row_count": 8}	\N	\N	\N
575	2	\N	admin	LDM	upload_file	Upload: iteminfo_weapon.staticinfo.xml	completed	100	Completed	\N	50	2026-03-16 05:05:37.585268	2026-03-16 05:05:37.689569	2026-03-16 05:05:37.689567	\N	\N	{"filename": "iteminfo_weapon.staticinfo.xml", "row_count": 50}	\N	\N	\N
576	2	\N	admin	LDM	upload_file	Upload: locstr_eng.xml	completed	100	Completed	\N	8	2026-03-16 05:05:37.738239	2026-03-16 05:05:37.83854	2026-03-16 05:05:37.838538	\N	\N	{"filename": "locstr_eng.xml", "row_count": 8}	\N	\N	\N
580	2	\N	admin	LDM	upload_file	Upload: languagedata_kor.xml	completed	100	Completed	\N	704	2026-03-16 05:06:03.22072	2026-03-16 05:06:03.507894	2026-03-16 05:06:03.507892	\N	\N	{"filename": "languagedata_kor.xml", "row_count": 704}	\N	\N	\N
577	2	\N	admin	LDM	upload_file	Upload: characterinfo_monster.staticinfo.xml	completed	100	Completed	\N	14	2026-03-16 05:06:02.694367	2026-03-16 05:06:02.788396	2026-03-16 05:06:02.788394	\N	\N	{"filename": "characterinfo_monster.staticinfo.xml", "row_count": 14}	\N	\N	\N
578	2	\N	admin	LDM	upload_file	Upload: characterinfo_npc_shop.staticinfo.xml	completed	100	Completed	\N	8	2026-03-16 05:06:02.867276	2026-03-16 05:06:02.967802	2026-03-16 05:06:02.9678	\N	\N	{"filename": "characterinfo_npc_shop.staticinfo.xml", "row_count": 8}	\N	\N	\N
579	2	\N	admin	LDM	upload_file	Upload: characterinfo_npc.staticinfo.xml	completed	100	Completed	\N	16	2026-03-16 05:06:03.047958	2026-03-16 05:06:03.130602	2026-03-16 05:06:03.1306	\N	\N	{"filename": "characterinfo_npc.staticinfo.xml", "row_count": 16}	\N	\N	\N
194	1	\N	dev_admin	LDM	upload_file	Upload: SMALLTESTFILEFORQUICKSEARCH.txt	completed	100	Completed	\N	1183	2025-12-30 16:47:50.43657	2025-12-30 16:47:51.313249	2025-12-30 16:47:51.313248	\N	\N	{"filename": "SMALLTESTFILEFORQUICKSEARCH.txt", "row_count": 1183}	\N	\N	\N
86	1	\N	neil	LDM	upload_file	Upload: test_10k.txt	completed	100	Completed	\N	10000	2025-12-25 07:28:19.417819	2025-12-25 07:28:24.014449	2025-12-25 07:28:24.014449	\N	\N	{"filename": "test_10k.txt", "row_count": 10000}	\N	\N	\N
90	1	\N	neil	LDM	upload_file	Upload: test_10k.txt	completed	100	Completed	\N	10000	2025-12-25 08:55:18.397124	2025-12-25 08:55:26.150656	2025-12-25 08:55:26.150656	\N	\N	{"filename": "test_10k.txt", "row_count": 10000}	\N	\N	\N
91	1	\N	neil	LDM	upload_file	Upload: test_10k.txt	completed	100	Completed	\N	10000	2025-12-25 08:57:54.47617	2025-12-25 08:58:01.923745	2025-12-25 08:58:01.923745	\N	\N	{"filename": "test_10k.txt", "row_count": 10000}	\N	\N	\N
450	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:00:51.02887	2026-03-14 11:00:51.551538	2026-03-14 11:00:51.551537	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
581	2	\N	admin	LDM	upload_file	Upload: brtag_up.xlsx	completed	100	Completed	\N	2	2026-03-16 17:51:55.662632	2026-03-16 17:51:55.774118	2026-03-16 17:51:55.774116	\N	\N	{"filename": "brtag_up.xlsx", "row_count": 2}	\N	\N	\N
582	2	\N	admin	LDM	upload_tm	Upload TM: BrTag-TXT-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:51:55.978183	2026-03-16 17:51:56.074316	2026-03-16 17:51:56.074315	\N	\N	{"mode": "standard", "name": "BrTag-TXT-TM", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
583	2	\N	admin	LDM	upload_tm	Upload TM: BrTag-TM-Entry	failed	30	Inserting entries...	\N	\N	2026-03-16 17:51:56.392147	2026-03-16 17:51:56.454129	2026-03-16 17:51:56.454128	\N	\N	{"mode": "standard", "name": "BrTag-TM-Entry", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
584	2	\N	admin	LDM	upload_tm	Upload TM: BrTag-TMSearch	failed	30	Inserting entries...	\N	\N	2026-03-16 17:51:56.708637	2026-03-16 17:51:56.777312	2026-03-16 17:51:56.777311	\N	\N	{"mode": "standard", "name": "BrTag-TMSearch", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
585	2	\N	admin	LDM	upload_file	Upload: characterinfo.xml	completed	100	Completed	\N	20	2026-03-16 17:52:34.257073	2026-03-16 17:52:34.354972	2026-03-16 17:52:34.35497	\N	\N	{"filename": "characterinfo.xml", "row_count": 20}	\N	\N	\N
586	2	\N	admin	LDM	upload_file	Upload: eu_14col_sample.xlsx	completed	100	Completed	\N	50	2026-03-16 17:52:34.447792	2026-03-16 17:52:34.565318	2026-03-16 17:52:34.565316	\N	\N	{"filename": "eu_14col_sample.xlsx", "row_count": 50}	\N	\N	\N
587	2	\N	admin	LDM	upload_file	Upload: mixed_brtags.xml	completed	100	Completed	\N	25	2026-03-16 17:52:35.547632	2026-03-16 17:52:35.635719	2026-03-16 17:52:35.635718	\N	\N	{"filename": "mixed_brtags.xml", "row_count": 25}	\N	\N	\N
452	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:00:51.264604	2026-03-14 11:00:51.700585	2026-03-14 11:00:51.700583	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
588	2	\N	admin	LDM	upload_tm	Upload TM: IntWf-Pretranslate-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:52:47.35764	2026-03-16 17:52:47.436059	2026-03-16 17:52:47.436058	\N	\N	{"mode": "standard", "name": "IntWf-Pretranslate-TM", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
596	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Upload-BrTag	failed	30	Inserting entries...	\N	\N	2026-03-16 17:53:18.546042	2026-03-16 17:53:18.624898	2026-03-16 17:53:18.624898	\N	\N	{"mode": "standard", "name": "E2E-Upload-BrTag", "filename": "brtag.txt"}	ValueError: No valid entries found in file	\N	\N
589	2	\N	admin	LDM	upload_file	Upload: kr_up.xlsx	completed	100	Completed	\N	2	2026-03-16 17:52:53.475349	2026-03-16 17:52:53.580532	2026-03-16 17:52:53.58053	\N	\N	{"filename": "kr_up.xlsx", "row_count": 2}	\N	\N	\N
590	2	\N	admin	LDM	upload_tm	Upload TM: Korean-TXT-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:52:53.797291	2026-03-16 17:52:53.874112	2026-03-16 17:52:53.874111	\N	\N	{"mode": "standard", "name": "Korean-TXT-TM", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
597	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Upload-Count	failed	30	Inserting entries...	\N	\N	2026-03-16 17:53:18.697504	2026-03-16 17:53:18.770933	2026-03-16 17:53:18.770933	\N	\N	{"mode": "standard", "name": "E2E-Upload-Count", "filename": "count.txt"}	ValueError: No valid entries found in file	\N	\N
591	2	\N	admin	LDM	upload_tm	Upload TM: Korean-TMSearch	failed	30	Inserting entries...	\N	\N	2026-03-16 17:52:55.558758	2026-03-16 17:52:55.647289	2026-03-16 17:52:55.647288	\N	\N	{"mode": "standard", "name": "Korean-TMSearch", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
592	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Test-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:52:57.864488	2026-03-16 17:52:57.949806	2026-03-16 17:52:57.949805	\N	\N	{"mode": "standard", "name": "E2E-Test-TM", "filename": "test_tm.txt"}	ValueError: No valid entries found in file	\N	\N
593	2	\N	admin	LDM	upload_tm	Upload TM: E2E-CRUD-Create	failed	30	Inserting entries...	\N	\N	2026-03-16 17:53:17.674109	2026-03-16 17:53:17.765982	2026-03-16 17:53:17.76598	\N	\N	{"mode": "standard", "name": "E2E-CRUD-Create", "filename": "crud.txt"}	ValueError: No valid entries found in file	\N	\N
594	2	\N	admin	LDM	upload_tm	Upload TM: E2E-CRUD-Delete	failed	30	Inserting entries...	\N	\N	2026-03-16 17:53:17.893815	2026-03-16 17:53:17.976931	2026-03-16 17:53:17.976931	\N	\N	{"mode": "standard", "name": "E2E-CRUD-Delete", "filename": "ephemeral.txt"}	ValueError: No valid entries found in file	\N	\N
595	2	\N	admin	LDM	upload_tm	Upload TM: E2E-Upload-TXT	failed	30	Inserting entries...	\N	\N	2026-03-16 17:53:18.274782	2026-03-16 17:53:18.424038	2026-03-16 17:53:18.424038	\N	\N	{"mode": "standard", "name": "E2E-Upload-TXT", "filename": "test.txt"}	ValueError: No valid entries found in file	\N	\N
599	2	\N	admin	LDM	upload_tm	Upload TM: BrTag-TXT-TM	failed	30	Inserting entries...	\N	\N	2026-03-16 17:54:18.797452	2026-03-16 17:54:18.872848	2026-03-16 17:54:18.872847	\N	\N	{"mode": "standard", "name": "BrTag-TXT-TM", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
462	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:28.752095	2026-03-14 11:05:28.854386	2026-03-14 11:05:28.854385	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
454	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:14.120692	2026-03-14 11:05:14.253884	2026-03-14 11:05:14.253883	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
511	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:31:53.910541	2026-03-16 01:31:54.016405	2026-03-16 01:31:54.016403	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
468	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:06:43.190221	2026-03-14 11:06:43.290889	2026-03-14 11:06:43.290887	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
455	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:14.379246	2026-03-14 11:05:14.481112	2026-03-14 11:05:14.48111	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
544	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:57:32.084795	2026-03-16 01:57:32.38138	2026-03-16 01:57:32.381378	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
515	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:31:54.776112	2026-03-16 01:31:54.880763	2026-03-16 01:31:54.880761	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
463	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:29.000782	2026-03-14 11:05:29.112487	2026-03-14 11:05:29.112485	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
456	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:14.568682	2026-03-14 11:05:14.6706	2026-03-14 11:05:14.670599	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
598	2	\N	admin	LDM	upload_file	Upload: brtag_up.xlsx	completed	100	Completed	\N	2	2026-03-16 17:54:18.435144	2026-03-16 17:54:18.578678	2026-03-16 17:54:18.578676	\N	\N	{"filename": "brtag_up.xlsx", "row_count": 2}	\N	\N	\N
512	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:31:54.126302	2026-03-16 01:31:54.23941	2026-03-16 01:31:54.239408	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
547	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:57:33.506605	2026-03-16 01:57:33.772909	2026-03-16 01:57:33.772907	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
457	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:14.759182	2026-03-14 11:05:14.860086	2026-03-14 11:05:14.860085	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
545	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:57:32.55346	2026-03-16 01:57:32.812564	2026-03-16 01:57:32.812561	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
464	2	\N	admin	LDM	upload_file	Upload: search_test_data.xml	completed	100	Completed	\N	10	2026-03-14 11:05:56.660819	2026-03-14 11:05:56.877761	2026-03-14 11:05:56.877758	\N	\N	{"filename": "search_test_data.xml", "row_count": 10}	\N	\N	\N
458	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:15.314967	2026-03-14 11:05:15.416936	2026-03-14 11:05:15.416934	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
513	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:31:54.32986	2026-03-16 01:31:54.434902	2026-03-16 01:31:54.434901	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
469	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:06:43.427346	2026-03-14 11:06:43.527894	2026-03-14 11:06:43.527892	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
459	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:28.133957	2026-03-14 11:05:28.261726	2026-03-14 11:05:28.261724	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
600	2	\N	admin	LDM	upload_tm	Upload TM: BrTag-TM-Entry	failed	30	Inserting entries...	\N	\N	2026-03-16 17:54:19.216264	2026-03-16 17:54:19.291894	2026-03-16 17:54:19.291893	\N	\N	{"mode": "standard", "name": "BrTag-TM-Entry", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
465	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:06:42.606154	2026-03-14 11:06:42.70668	2026-03-14 11:06:42.706678	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
460	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:28.346923	2026-03-14 11:05:28.448674	2026-03-14 11:05:28.448673	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
514	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:31:54.525151	2026-03-16 01:31:54.63094	2026-03-16 01:31:54.630938	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
546	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:57:33.002148	2026-03-16 01:57:33.323803	2026-03-16 01:57:33.323802	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
461	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:05:28.535948	2026-03-14 11:05:28.637998	2026-03-14 11:05:28.637996	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
548	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:57:34.137301	2026-03-16 01:57:34.381521	2026-03-16 01:57:34.381519	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
601	2	\N	admin	LDM	upload_tm	Upload TM: BrTag-TMSearch	failed	30	Inserting entries...	\N	\N	2026-03-16 17:54:19.586519	2026-03-16 17:54:19.719985	2026-03-16 17:54:19.719985	\N	\N	{"mode": "standard", "name": "BrTag-TMSearch", "filename": "tm.txt"}	ValueError: No valid entries found in file	\N	\N
466	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:06:42.793853	2026-03-14 11:06:42.893364	2026-03-14 11:06:42.893362	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
602	2	\N	admin	LDM	upload_file	Upload: characterinfo.xml	completed	100	Completed	\N	20	2026-03-16 17:54:37.159814	2026-03-16 17:54:37.271869	2026-03-16 17:54:37.271866	\N	\N	{"filename": "characterinfo.xml", "row_count": 20}	\N	\N	\N
603	2	\N	admin	LDM	upload_file	Upload: eu_14col_sample.xlsx	completed	100	Completed	\N	50	2026-03-16 17:54:37.360601	2026-03-16 17:54:37.471639	2026-03-16 17:54:37.471637	\N	\N	{"filename": "eu_14col_sample.xlsx", "row_count": 50}	\N	\N	\N
467	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-14 11:06:42.986634	2026-03-14 11:06:43.087489	2026-03-14 11:06:43.087487	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
604	2	\N	admin	LDM	upload_file	Upload: mixed_brtags.xml	completed	100	Completed	\N	25	2026-03-16 17:54:38.435212	2026-03-16 17:54:38.537183	2026-03-16 17:54:38.537181	\N	\N	{"filename": "mixed_brtags.xml", "row_count": 25}	\N	\N	\N
379	1	\N	testuser	LDM	upload_tm	Upload TM: Test TM	failed	30	Inserting entries...	\N	\N	2026-01-13 16:20:27.714056	2026-01-13 16:20:27.855826	2026-01-13 16:20:27.855825	\N	\N	{"mode": "standard", "name": "Test TM", "filename": "test.txt"}	ValueError: No valid entries found in file	\N	\N
406	1	\N	testuser	LDM	upload_tm	Upload TM: Test TM	failed	30	Inserting entries...	\N	\N	2026-01-14 04:13:46.859222	2026-01-14 04:13:46.944724	2026-01-14 04:13:46.944723	\N	\N	{"mode": "standard", "name": "Test TM", "filename": "test.txt"}	ValueError: No valid entries found in file	\N	\N
497	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:12:29.879405	2026-03-16 01:12:29.994661	2026-03-16 01:12:29.994628	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
525	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:51:05.500606	2026-03-16 01:51:05.772972	2026-03-16 01:51:05.77297	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
498	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:12:30.087704	2026-03-16 01:12:30.195897	2026-03-16 01:12:30.195895	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
526	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:51:05.962148	2026-03-16 01:51:06.264282	2026-03-16 01:51:06.26428	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
499	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:12:30.289219	2026-03-16 01:12:30.406629	2026-03-16 01:12:30.406626	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
527	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:51:06.46041	2026-03-16 01:51:06.711543	2026-03-16 01:51:06.711541	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
500	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:12:30.499556	2026-03-16 01:12:30.60791	2026-03-16 01:12:30.607909	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
501	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:12:30.756367	2026-03-16 01:12:30.864018	2026-03-16 01:12:30.864017	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
528	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:51:06.870669	2026-03-16 01:51:07.150025	2026-03-16 01:51:07.150022	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
529	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:51:07.457855	2026-03-16 01:51:07.758491	2026-03-16 01:51:07.758489	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
530	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:56:15.307426	2026-03-16 01:56:15.640788	2026-03-16 01:56:15.640786	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
531	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:56:15.830495	2026-03-16 01:56:16.093675	2026-03-16 01:56:16.093673	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
532	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:56:16.287079	2026-03-16 01:56:16.579575	2026-03-16 01:56:16.579573	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
533	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:56:16.795813	2026-03-16 01:56:17.074578	2026-03-16 01:56:17.074576	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
534	2	\N	admin	LDM	upload_file	Upload: roundtrip_test.xml	completed	100	Completed	\N	5	2026-03-16 01:56:17.424338	2026-03-16 01:56:17.688882	2026-03-16 01:56:17.68888	\N	\N	{"filename": "roundtrip_test.xml", "row_count": 5}	\N	\N	\N
562	51	\N	logtest_user	Test	test	Op 0	running	0	\N	\N	0	2026-03-16 02:40:53.873239	2026-03-16 02:40:53.873241	\N	\N	null	null	\N	\N	null
563	51	\N	logtest_user	Test	test	Op 1	completed	0	\N	\N	0	2026-03-16 02:40:53.873242	2026-03-16 02:40:53.873242	\N	\N	null	null	\N	\N	null
564	51	\N	logtest_user	Test	test	Op 2	running	0	\N	\N	0	2026-03-16 02:40:53.873242	2026-03-16 02:40:53.873243	\N	\N	null	null	\N	\N	null
565	51	\N	logtest_user	Test	test	Op 3	failed	0	\N	\N	0	2026-03-16 02:40:53.873243	2026-03-16 02:40:53.873243	\N	\N	null	null	\N	\N	null
566	51	\N	logtest_user	Test	test	Op 4	running	0	\N	\N	0	2026-03-16 02:40:53.873244	2026-03-16 02:40:53.873244	\N	\N	null	null	\N	\N	null
195	1	\N	dev_admin	LDM	upload_file	Upload: sampleofLanguageData.txt	completed	100	Completed	\N	103500	2025-12-30 16:47:54.604335	2025-12-30 16:48:33.062171	2025-12-30 16:48:33.062169	\N	\N	{"filename": "sampleofLanguageData.txt", "row_count": 103500}	\N	\N	\N
196	1	\N	dev_admin	LDM	upload_file	Upload: languagedata_fr PC 1012 1813.txt	completed	100	Completed	\N	1103032	2025-12-30 16:49:09.270062	2025-12-30 16:56:15.339614	2025-12-30 16:56:15.339612	\N	\N	{"filename": "languagedata_fr PC 1012 1813.txt", "row_count": 1103032}	\N	\N	\N
\.


--
-- Data for Name: announcements; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.announcements (announcement_id, title, message, priority, created_at, expires_at, is_active, target_users) FROM stdin;
\.


--
-- Data for Name: app_versions; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.app_versions (version_id, version_number, release_date, is_latest, is_required, release_notes, download_url) FROM stdin;
\.


--
-- Data for Name: error_logs; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.error_logs (error_id, "timestamp", user_id, machine_id, tool_name, function_name, error_type, error_message, stack_trace, app_version, context) FROM stdin;
\.


--
-- Data for Name: function_usage_stats; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.function_usage_stats (stat_id, date, tool_name, function_name, total_uses, unique_users, total_duration_seconds, avg_duration_seconds, min_duration_seconds, max_duration_seconds) FROM stdin;
\.


--
-- Data for Name: installations; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.installations (installation_id, api_key_hash, installation_name, version, owner_email, is_active, created_at, last_seen, last_version, extra_data) FROM stdin;
mn2fWJtp3-SwBjxNnaTnGA	0b4176fb3548729f803b1099f7afc520ebbb997c4dc6a6fb72fb1c480981036a	Test Desktop	1.2.0	\N	t	2026-01-31 06:28:48.846047	2026-01-31 06:28:52.227542	1.2.0	null
WumatQvn4rsS7-t3sWNsNw	3ca57e0b48d75853f09208c8888cce4ccbd588f32711a904112c8fb2b3737731	Workflow Test	1.2.0	\N	t	2026-01-31 06:28:52.670119	2026-01-31 06:28:53.916501	1.2.0	null
\.


--
-- Data for Name: ldm_active_sessions; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_active_sessions (id, file_id, user_id, cursor_row, editing_row, joined_at, last_seen) FROM stdin;
\.


--
-- Data for Name: ldm_active_tms; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_active_tms (id, tm_id, project_id, file_id, priority, activated_by, activated_at) FROM stdin;
\.


--
-- Data for Name: ldm_backups; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_backups (id, backup_type, project_id, file_id, tm_id, backup_path, file_size, status, error_message, trigger, created_by, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: ldm_edit_history; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_edit_history (id, row_id, user_id, old_target, new_target, old_status, new_status, edited_at) FROM stdin;
\.


--
-- Data for Name: ldm_files; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_files (id, project_id, folder_id, name, original_filename, format, row_count, source_language, target_language, created_at, updated_at, created_by, extra_data) FROM stdin;
\.


--
-- Data for Name: ldm_folders; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_folders (id, project_id, parent_id, name, created_at) FROM stdin;
\.


--
-- Data for Name: ldm_platforms; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_platforms (id, name, owner_id, description, created_at, updated_at, is_restricted) FROM stdin;
112	Offline Storage	1	Local files stored offline for translation	2026-03-16 17:52:44.294572	2026-03-16 17:52:44.294575	f
\.


--
-- Data for Name: ldm_projects; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_projects (id, name, owner_id, description, created_at, updated_at, platform_id, is_restricted) FROM stdin;
230	test_project_4	2	\N	2026-03-16 17:54:11.623119	2026-03-16 17:54:11.62312	\N	f
281	test_project_5	2	\N	2026-03-16 17:56:11.05841	2026-03-16 17:56:11.058412	\N	f
172	test_project	2	\N	2026-03-16 17:48:53.714792	2026-03-16 17:48:53.714794	\N	f
283	test_project_6	2	\N	2026-03-16 17:56:31.927732	2026-03-16 17:56:31.927733	\N	f
174	test_project_1	2	\N	2026-03-16 17:50:01.906385	2026-03-16 17:50:01.906386	\N	f
176	test_project_2	2	\N	2026-03-16 17:50:55.467623	2026-03-16 17:50:55.467625	\N	f
178	test_project_3	2	\N	2026-03-16 17:51:50.208198	2026-03-16 17:51:50.2082	\N	f
257	IntWf-Cascade_1	2	\N	2026-03-16 17:54:55.642372	2026-03-16 17:54:55.642374	\N	f
258	IntWf-PostDelete_1	2	\N	2026-03-16 17:54:55.768252	2026-03-16 17:54:55.768254	\N	f
259	IntWf-Lifecycle_1	2	\N	2026-03-16 17:54:55.893802	2026-03-16 17:54:55.893804	\N	f
197	Offline Storage	1	Local files stored offline	2026-03-16 17:52:44.298938	2026-03-16 17:52:44.29894	112	f
206	IntWf-Cascade	2	\N	2026-03-16 17:52:54.096017	2026-03-16 17:52:54.096019	\N	f
207	IntWf-PostDelete	2	\N	2026-03-16 17:52:54.228161	2026-03-16 17:52:54.228164	\N	f
208	IntWf-Lifecycle	2	\N	2026-03-16 17:52:54.357711	2026-03-16 17:52:54.357713	\N	f
\.


--
-- Data for Name: ldm_qa_results; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_qa_results (id, row_id, file_id, check_type, severity, message, details, created_at, resolved_at, resolved_by) FROM stdin;
\.


--
-- Data for Name: ldm_resource_access; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_resource_access (id, platform_id, project_id, user_id, access_level, granted_by, granted_at) FROM stdin;
\.


--
-- Data for Name: ldm_rows; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_rows (id, file_id, row_num, string_id, source, target, status, updated_by, updated_at, extra_data, qa_checked_at, qa_flag_count) FROM stdin;
\.


--
-- Data for Name: ldm_tm_assignments; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_tm_assignments (id, tm_id, platform_id, project_id, folder_id, is_active, priority, assigned_by, assigned_at, activated_at) FROM stdin;
\.


--
-- Data for Name: ldm_tm_entries; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_tm_entries (id, tm_id, source_text, target_text, source_hash, created_by, change_date, created_at, string_id, updated_at, is_confirmed, confirmed_at, confirmed_by, updated_by) FROM stdin;
\.


--
-- Data for Name: ldm_tm_indexes; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_tm_indexes (id, tm_id, index_type, index_path, entry_count, file_size, status, error_message, created_at, built_at) FROM stdin;
\.


--
-- Data for Name: ldm_translation_memories; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_translation_memories (id, name, description, owner_id, source_lang, target_lang, entry_count, whole_pairs, line_pairs, status, error_message, storage_path, created_at, updated_at, indexed_at, mode) FROM stdin;
\.


--
-- Data for Name: ldm_trash; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.ldm_trash (id, item_type, item_id, item_name, parent_project_id, parent_folder_id, item_data, deleted_by, deleted_at, expires_at, status) FROM stdin;
230	project	276	DeleteTest-1773683715	\N	\N	{"name": "DeleteTest-1773683715", "files": [], "folders": [], "description": null, "platform_id": null, "is_restricted": false}	2	2026-03-16 17:55:15.159057	2026-04-15 17:55:15.157878	trashed
\.


--
-- Data for Name: log_entries; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.log_entries (log_id, user_id, session_id, username, machine_id, tool_name, function_name, "timestamp", duration_seconds, status, error_message, file_info, parameters) FROM stdin;
1	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-16 05:45:06.798469	5.5	success	\N	null	null
2	25	\N	log_test_1765831510	test-machine	TestTool	test_function	2025-12-16 05:45:10.972275	10.5	success	\N	null	null
58	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-22 03:34:55.321923	5.5	success	\N	null	null
59	169	\N	log_test_1766342100	test-machine	TestTool	test_function	2025-12-22 03:35:08.984881	10.5	success	\N	null	null
60	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-22 03:35:46.151434	5.5	success	\N	null	null
61	206	\N	log_test_1766342150	test-machine	TestTool	test_function	2025-12-22 03:35:50.585025	10.5	success	\N	null	null
138	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-22 05:50:08.578584	5.5	success	\N	null	null
139	384	\N	log_test_1766350213	test-machine	TestTool	test_function	2025-12-22 05:50:22.328537	10.5	success	\N	null	null
216	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-01-13 16:23:00.086025	5.5	success	\N	null	null
217	549	\N	log_test_1768288981	test-machine	TestTool	test_function	2026-01-13 16:23:02.185384	10.5	success	\N	null	null
294	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 01:31:42.111217	5.5	success	\N	null	null
295	752	\N	log_test_1773592307	test-machine	TestTool	test_function	2026-03-16 01:31:47.462184	10.5	success	\N	null	null
370	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 02:40:39.909881	5.5	success	\N	null	null
20	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-21 13:41:11.271156	5.5	success	\N	null	null
21	94	\N	log_test_1766292076	test-machine	TestTool	test_function	2025-12-21 13:41:16.612576	10.5	success	\N	null	null
79	243	\N	log_test_1766347359	test-machine	TestTool	test_function	2025-12-22 05:02:39.914901	10.5	success	\N	null	null
80	258	\N	log_test_1766347402	test-machine	TestTool	test_function	2025-12-22 05:03:22.354717	10.5	success	\N	null	null
81	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-22 05:25:05.558535	5.5	success	\N	null	null
82	273	\N	log_test_1766348710	test-machine	TestTool	test_function	2025-12-22 05:25:10.539696	10.5	success	\N	null	null
157	431	\N	log_test_1766820952	test-machine	TestTool	test_function	2025-12-27 16:35:52.887821	10.5	success	\N	null	null
235	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-01-14 04:13:23.573067	5.5	success	\N	null	null
236	586	\N	log_test_1768331607	test-machine	TestTool	test_function	2026-01-14 04:13:28.221494	10.5	success	\N	null	null
39	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-22 02:20:39.534681	5.5	success	\N	null	null
40	131	\N	log_test_1766337643	test-machine	TestTool	test_function	2025-12-22 02:20:43.855829	10.5	success	\N	null	null
313	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 01:50:51.773617	5.5	success	\N	null	null
314	789	\N	log_test_1773593456	test-machine	TestTool	test_function	2026-03-16 01:50:57.224272	10.5	success	\N	null	null
100	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-22 05:29:42.669025	5.5	success	\N	null	null
101	310	\N	log_test_1766348986	test-machine	TestTool	test_function	2025-12-22 05:29:47.131398	10.5	success	\N	null	null
175	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-28 08:30:06.653494	5.5	success	\N	null	null
176	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-28 08:32:00.7568	5.5	success	\N	null	null
177	468	\N	log_test_1766878325	test-machine	TestTool	test_function	2025-12-28 08:32:05.808875	10.5	success	\N	null	null
254	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 01:08:44.256531	5.5	success	\N	null	null
255	641	\N	log_test_1773590926	test-machine	TestTool	test_function	2026-03-16 01:08:47.236411	10.5	success	\N	null	null
256	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 01:10:17.524824	5.5	success	\N	null	null
257	678	\N	log_test_1773591021	test-machine	TestTool	test_function	2026-03-16 01:10:22.146638	10.5	success	\N	null	null
119	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-22 05:31:50.394477	5.5	success	\N	null	null
120	347	\N	log_test_1766349114	test-machine	TestTool	test_function	2025-12-22 05:31:54.889883	10.5	success	\N	null	null
332	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 01:57:16.286841	5.5	success	\N	null	null
333	826	\N	log_test_1773593842	test-machine	TestTool	test_function	2026-03-16 01:57:22.665426	10.5	success	\N	null	null
195	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-28 08:32:27.803507	5.5	success	\N	null	null
196	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2025-12-28 09:04:02.826271	5.5	success	\N	null	null
197	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-01-12 13:04:10.413144	5.5	success	\N	null	null
198	512	\N	log_test_1768190654	test-machine	TestTool	test_function	2026-01-12 13:04:14.921453	10.5	success	\N	null	null
275	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 01:12:16.794408	5.5	success	\N	null	null
276	715	\N	log_test_1773591141	test-machine	TestTool	test_function	2026-03-16 01:12:21.473623	10.5	success	\N	null	null
371	900	\N	log_test_1773596444	test-machine	TestTool	test_function	2026-03-16 02:40:45.258275	10.5	success	\N	null	null
351	13	\N	testuser	test-machine-001	XLSTransfer	create_dictionary	2026-03-16 02:37:25.731862	5.5	success	\N	null	null
352	863	\N	log_test_1773596251	test-machine	TestTool	test_function	2026-03-16 02:37:31.95993	10.5	success	\N	null	null
\.


--
-- Data for Name: performance_metrics; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.performance_metrics (metric_id, "timestamp", tool_name, function_name, duration_seconds, cpu_usage_percent, memory_mb, file_size_mb, rows_processed) FROM stdin;
\.


--
-- Data for Name: remote_logs; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.remote_logs (log_id, installation_id, "timestamp", level, message, data, source, component, received_at) FROM stdin;
1	mn2fWJtp3-SwBjxNnaTnGA	2026-01-31 06:28:49.467945	INFO	XLSTransfer: Load dictionary clicked	null	frontend	XLSTransfer	2026-01-31 06:28:49.728083
2	mn2fWJtp3-SwBjxNnaTnGA	2026-01-31 06:28:49.467957	INFO	Dictionary loaded: 1500 entries	null	backend	XLSTransfer	2026-01-31 06:28:49.728085
3	mn2fWJtp3-SwBjxNnaTnGA	2026-01-31 06:28:49.467958	WARNING	Slow response: 2.3s	null	backend	API	2026-01-31 06:28:49.728086
4	mn2fWJtp3-SwBjxNnaTnGA	2026-01-31 06:28:50.218509	ERROR	Failed to connect to backend: ECONNREFUSED	{"url": "http://127.0.0.1:8888/health"}	frontend	API	2026-01-31 06:28:50.361907
5	WumatQvn4rsS7-t3sWNsNw	2026-01-31 06:28:53.676289	INFO	XLSTransfer: Starting load dictionary	null	frontend	XLSTransfer	2026-01-31 06:28:53.756653
6	WumatQvn4rsS7-t3sWNsNw	2026-01-31 06:28:53.676297	INFO	Processing 1500 rows	null	backend	XLSTransfer	2026-01-31 06:28:53.756655
7	WumatQvn4rsS7-t3sWNsNw	2026-01-31 06:28:53.676299	INFO	Dictionary loaded successfully	null	backend	XLSTransfer	2026-01-31 06:28:53.756656
\.


--
-- Data for Name: remote_sessions; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.remote_sessions (session_id, installation_id, started_at, ended_at, last_heartbeat, duration_seconds, ip_address, app_version, is_active, end_reason) FROM stdin;
473190d6-42be-4b1a-96d7-dcd4473b71b2	mn2fWJtp3-SwBjxNnaTnGA	2026-01-31 06:28:49.245767	2026-01-31 06:28:51.839709	2026-01-31 06:28:49.24577	2	\N	1.2.0	f	user_closed
cfe877d5-74fb-4c78-aae2-07e2b40c289e	WumatQvn4rsS7-t3sWNsNw	2026-01-31 06:28:53.605098	2026-01-31 06:28:53.951947	2026-01-31 06:28:53.6051	0	\N	1.2.0	f	user_closed
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.sessions (session_id, user_id, machine_id, ip_address, app_version, session_start, last_activity, is_active) FROM stdin;
67721fd0-10f5-4cc3-9935-c4b6949c6ace	13	test-machine-001	127.0.0.1	1.0.0	2025-12-16 05:45:07.457375	2025-12-16 05:45:07.457375	t
4fd3c474-9445-4856-85a5-82ce4c822c48	26	test-machine-001	127.0.0.1	1.0.0-test	2025-12-16 05:45:11.283202	2025-12-16 05:45:11.283203	t
4c872be8-084e-4de2-ba97-7ab7eafa21c5	107	login_machine_8f7b6553	10.0.0.1	1.0.0	2025-12-21 13:41:19.395046	2025-12-21 13:41:19.39505	t
421b8edc-c7f7-4c62-a938-1edae128839c	27	test-machine-002	127.0.0.1	1.0.0-test	2025-12-16 05:45:11.573133	2025-12-16 05:45:11.622122	f
af2dfdc6-67a6-4a80-9d4d-86ee118d7fc4	28	test-machine-000	127.0.0.1	1.0.0-test	2025-12-16 05:45:11.866736	2025-12-16 05:45:11.866738	t
6f412055-0006-4e21-b0ea-59451125e01a	28	test-machine-001	127.0.0.1	1.0.0-test	2025-12-16 05:45:11.866801	2025-12-16 05:45:11.866801	t
8cfd1638-c5c0-4572-a5c4-686101a4c470	28	test-machine-002	127.0.0.1	1.0.0-test	2025-12-16 05:45:11.866877	2025-12-16 05:45:11.866878	f
b58a2e83-b110-4d6c-b66b-1f3d7ca784bf	32	test_machine_aa0f8f77	192.168.1.100	2512010029	2025-12-16 05:45:12.554764	2025-12-16 05:45:12.554766	t
98526a64-48ea-4019-b1d9-cded65f7774c	33	machine_1e2f794c_0	\N	1.0.0	2025-12-16 05:45:12.621887	2025-12-16 05:45:12.621888	t
d47b0a3c-7ab4-4ef3-bf91-7a971b96b1cf	33	machine_1e2f794c_1	\N	1.0.0	2025-12-16 05:45:12.621894	2025-12-16 05:45:12.621894	t
6ed9b68e-c587-43ff-a148-31a064062a39	33	machine_1e2f794c_2	\N	1.0.0	2025-12-16 05:45:12.621898	2025-12-16 05:45:12.621898	t
386f38ca-87ee-4a34-9e4a-4a679ed1ca63	34	machine_f858a480	\N	1.0.0	2025-12-16 05:45:12.689816	2025-12-16 05:45:12.710581	f
915ce5e8-72d6-4717-a4e2-45ff911c3c00	35	machine_468be304	\N	1.0.0	2025-12-16 05:45:12.778094	2025-12-16 05:45:12.898227	t
20688368-d6e5-4907-a896-3025f8eb53a7	36	machine_be40e1e6_0	\N	1.0.0	2025-12-16 05:45:12.966685	2025-12-16 05:45:12.966686	t
dfab8e71-5fbe-4d44-9827-92a9f0c3cf84	36	machine_be40e1e6_1	\N	1.0.0	2025-12-16 05:45:12.966691	2025-12-16 05:45:12.966691	f
c8b24bb3-7be1-483d-9e17-fce258c93ccd	36	machine_be40e1e6_2	\N	1.0.0	2025-12-16 05:45:12.966695	2025-12-16 05:45:12.966695	t
dc68c78f-87e7-4642-9672-69d7d89f3c08	36	machine_be40e1e6_3	\N	1.0.0	2025-12-16 05:45:12.966698	2025-12-16 05:45:12.966698	f
d9396d8f-5ae9-4273-b474-2a3336218b94	36	machine_be40e1e6_4	\N	1.0.0	2025-12-16 05:45:12.966701	2025-12-16 05:45:12.966702	t
351f4545-7d0b-4109-9257-57e2809e8979	38	login_machine_1ba45a66	10.0.0.1	1.0.0	2025-12-16 05:45:13.101688	2025-12-16 05:45:13.101689	t
99bcbf5f-4d21-4d12-9d69-ad6b2d3e21c8	55	test_machine_1d7ed5b8	192.168.1.100	2512010029	2025-12-16 05:46:57.256467	2025-12-16 05:46:57.256469	t
5ed3d4da-2dbb-477b-89df-6abbc96bf311	56	machine_8bbda1de_0	\N	1.0.0	2025-12-16 05:46:57.323808	2025-12-16 05:46:57.32381	t
93dc67bc-fcf7-4442-9437-c77839690bac	56	machine_8bbda1de_1	\N	1.0.0	2025-12-16 05:46:57.323816	2025-12-16 05:46:57.323816	t
1aa1a34f-e617-4c72-a7cb-6511ab25a4aa	56	machine_8bbda1de_2	\N	1.0.0	2025-12-16 05:46:57.323819	2025-12-16 05:46:57.32382	t
5cf8a016-ea0a-43ac-9012-8a1204ac6832	57	machine_780fb52e	\N	1.0.0	2025-12-16 05:46:57.403522	2025-12-16 05:46:57.423516	f
fde7edb6-f489-4170-baa9-a24d34f01c85	58	machine_9652c073	\N	1.0.0	2025-12-16 05:46:57.555498	2025-12-16 05:46:57.722441	t
9ede707b-a084-443e-9a06-2d4102adacc3	59	machine_6493649b_0	\N	1.0.0	2025-12-16 05:46:57.794372	2025-12-16 05:46:57.794373	t
c3e3df86-5a7a-49da-84c4-603d720ded7b	59	machine_6493649b_1	\N	1.0.0	2025-12-16 05:46:57.794379	2025-12-16 05:46:57.794379	f
3c742b10-f910-4598-8887-df16a5f1c631	59	machine_6493649b_2	\N	1.0.0	2025-12-16 05:46:57.794382	2025-12-16 05:46:57.794382	t
0c7cc972-cf4b-48d0-a190-868010c8218e	59	machine_6493649b_3	\N	1.0.0	2025-12-16 05:46:57.794386	2025-12-16 05:46:57.794386	f
04212e58-bbf0-49d7-b56b-2f79a83bce61	59	machine_6493649b_4	\N	1.0.0	2025-12-16 05:46:57.794389	2025-12-16 05:46:57.794389	t
3970ef16-ddb2-4a36-a0de-b7dec225285f	61	login_machine_a9d12fe4	10.0.0.1	1.0.0	2025-12-16 05:46:57.938095	2025-12-16 05:46:57.938096	t
b9dd5203-8811-4360-9dbf-fd1860c055fa	13	test-machine-001	127.0.0.1	1.0.0	2025-12-21 13:41:19.848755	2025-12-21 13:41:19.848757	t
656b0027-d698-42f8-a642-979017a5ec7e	95	test-machine-001	127.0.0.1	1.0.0-test	2025-12-21 13:41:17.023883	2025-12-21 13:41:17.023885	t
772bf8fd-b447-4173-824e-e50e495adfa5	13	test-machine-001	127.0.0.1	1.0.0	2025-12-22 02:20:40.092671	2025-12-22 02:20:40.092672	t
f2e1ac1a-b2d7-4c13-a9df-568461a69996	96	test-machine-002	127.0.0.1	1.0.0-test	2025-12-21 13:41:16.992345	2025-12-21 13:41:17.092683	f
02742a4f-74f2-4d2e-a88f-0e2c8f08da51	97	test-machine-000	127.0.0.1	1.0.0-test	2025-12-21 13:41:17.469406	2025-12-21 13:41:17.469408	t
99551ff8-0b76-4b9d-8910-0dfe0faf374c	97	test-machine-001	127.0.0.1	1.0.0-test	2025-12-21 13:41:17.46951	2025-12-21 13:41:17.469511	t
6fda7a80-eca3-4bcb-a6c2-65a836918673	97	test-machine-002	127.0.0.1	1.0.0-test	2025-12-21 13:41:17.469567	2025-12-21 13:41:17.469567	f
86edfb17-5831-4210-a881-fabcc799ec02	101	test_machine_70c5b254	192.168.1.100	2512010029	2025-12-21 13:41:18.408523	2025-12-21 13:41:18.408527	t
55131b37-ad7f-472d-b7c6-d08bd482a4f9	102	machine_46ffb24b_0	\N	1.0.0	2025-12-21 13:41:18.549925	2025-12-21 13:41:18.549929	t
b97f7df2-d552-4e4a-b071-ec38710e369c	102	machine_46ffb24b_1	\N	1.0.0	2025-12-21 13:41:18.549941	2025-12-21 13:41:18.549941	t
b24cd80a-880c-4ba8-9e0d-bdfc1020060f	102	machine_46ffb24b_2	\N	1.0.0	2025-12-21 13:41:18.549949	2025-12-21 13:41:18.54995	t
db3918f6-b310-4b86-9f53-06fa58c33823	103	machine_762f4549	\N	1.0.0	2025-12-21 13:41:18.651285	2025-12-21 13:41:18.686146	f
768235c3-d780-4fee-909d-7c96698a51fe	104	machine_3b8aaafa	\N	1.0.0	2025-12-21 13:41:18.797696	2025-12-21 13:41:18.923288	t
152892c4-7452-4d3c-a232-ae424aa4d377	105	machine_71f1d056_0	\N	1.0.0	2025-12-21 13:41:19.082611	2025-12-21 13:41:19.082614	t
6c67c001-2c46-4bfa-aeb7-6ea27661ad34	105	machine_71f1d056_1	\N	1.0.0	2025-12-21 13:41:19.082624	2025-12-21 13:41:19.082625	f
aaaa5518-9623-46bc-8204-f487b193f15e	105	machine_71f1d056_2	\N	1.0.0	2025-12-21 13:41:19.082631	2025-12-21 13:41:19.082632	t
37196732-6bcf-42f7-ada5-2c4479b10073	105	machine_71f1d056_3	\N	1.0.0	2025-12-21 13:41:19.082638	2025-12-21 13:41:19.082638	f
07f71b0d-5357-44d7-823c-051092120deb	105	machine_71f1d056_4	\N	1.0.0	2025-12-21 13:41:19.082646	2025-12-21 13:41:19.082646	t
f6079b53-e0ed-4f05-b09f-5c32c16c660c	132	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 02:20:44.301434	2025-12-22 02:20:44.301437	t
3dddfd5c-95f0-46af-9dc6-4a696f571514	138	test_machine_36f1176f	192.168.1.100	2512010029	2025-12-22 02:20:45.861883	2025-12-22 02:20:45.861885	t
0bb52a4d-344a-4e33-97f1-c57d06f5a0f0	133	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 02:20:44.662636	2025-12-22 02:20:44.811471	f
9a5da706-092b-4821-afb2-946b35f56dbe	134	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 02:20:45.176065	2025-12-22 02:20:45.176067	t
63de1053-4d76-4eeb-9d9d-234144a898c1	134	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 02:20:45.17617	2025-12-22 02:20:45.176171	t
04cce607-d7bc-4384-80ca-f01e8c1374b3	134	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 02:20:45.176224	2025-12-22 02:20:45.176224	f
159cbc22-7d63-4859-a1fd-eb4d4255ee32	139	machine_30829963_0	\N	1.0.0	2025-12-22 02:20:45.935664	2025-12-22 02:20:45.935667	t
bce88be3-3999-460b-a538-eedb68730300	139	machine_30829963_1	\N	1.0.0	2025-12-22 02:20:45.935676	2025-12-22 02:20:45.935677	t
ee4108b7-71a8-4667-812d-d07e59507618	139	machine_30829963_2	\N	1.0.0	2025-12-22 02:20:45.935685	2025-12-22 02:20:45.935685	t
2e648203-b66b-4425-8cf6-80d0e26659b0	140	machine_58fb852c	\N	1.0.0	2025-12-22 02:20:46.017723	2025-12-22 02:20:46.041317	f
26451e8d-9c7d-4c99-98f1-f5cfaa87cbdc	141	machine_f7f46a08	\N	1.0.0	2025-12-22 02:20:46.115735	2025-12-22 02:20:46.2556	t
c0fcaa26-edaa-4887-ab3e-fcc70ba018e2	142	machine_a826fb17_0	\N	1.0.0	2025-12-22 02:20:46.354598	2025-12-22 02:20:46.3546	t
7add2b64-8f1b-4c35-8760-cbfcf8f58a91	142	machine_a826fb17_1	\N	1.0.0	2025-12-22 02:20:46.354609	2025-12-22 02:20:46.35461	f
648a0b09-7378-4a17-8361-dee22ecc2da5	142	machine_a826fb17_2	\N	1.0.0	2025-12-22 02:20:46.354617	2025-12-22 02:20:46.354618	t
101f9be0-e11c-4fa5-b98b-c9cfb6d64759	142	machine_a826fb17_3	\N	1.0.0	2025-12-22 02:20:46.354624	2025-12-22 02:20:46.354625	f
0210b304-4d37-43b4-9069-5b4c7baa119c	142	machine_a826fb17_4	\N	1.0.0	2025-12-22 02:20:46.354632	2025-12-22 02:20:46.354633	t
85c5add9-e934-4358-9b56-ff361ec05cb2	144	login_machine_d6bf959b	10.0.0.1	1.0.0	2025-12-22 02:20:46.597785	2025-12-22 02:20:46.597787	t
4fcd4eef-f1b2-4820-b1f9-3f0554a0fa31	13	test-machine-001	127.0.0.1	1.0.0	2025-12-22 03:34:55.983952	2025-12-22 03:34:55.983953	t
82335d4d-8404-47a7-8c8f-bef53b5f6e17	170	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 03:35:00.209103	2025-12-22 03:35:00.209106	t
c82cba78-6e77-49cb-a0ab-8397739d4224	171	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 03:35:00.646905	2025-12-22 03:35:00.767439	f
83ee1859-0e3e-4706-b1fc-ad2dd4a718a0	172	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 03:35:01.164017	2025-12-22 03:35:01.164019	t
376aa214-aeb5-4ed8-a07e-35ac6f2a2ee4	172	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 03:35:01.164113	2025-12-22 03:35:01.164113	t
510d82be-b034-420e-af8a-a37a93a4e38e	172	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 03:35:01.164167	2025-12-22 03:35:01.164167	f
0cadb41e-1b05-42ca-9133-8958891a431e	176	test_machine_4971ee29	192.168.1.100	2512010029	2025-12-22 03:35:01.940607	2025-12-22 03:35:01.940609	t
ea0786e3-8a3e-4bc3-938b-cd2b0736b236	177	machine_c1cf6401_0	\N	1.0.0	2025-12-22 03:35:02.02366	2025-12-22 03:35:02.023663	t
34a6f943-8aca-494e-8bc1-286c80ca4761	177	machine_c1cf6401_1	\N	1.0.0	2025-12-22 03:35:02.023673	2025-12-22 03:35:02.023673	t
179f2904-4bc0-4e83-a4ea-aed1812dc606	177	machine_c1cf6401_2	\N	1.0.0	2025-12-22 03:35:02.023681	2025-12-22 03:35:02.023682	t
c008324b-6587-497e-b933-96362b5081ce	178	machine_29023c19	\N	1.0.0	2025-12-22 03:35:02.105531	2025-12-22 03:35:02.127753	f
37141cb6-6468-4a3e-b321-82682b08f392	179	machine_a9136657	\N	1.0.0	2025-12-22 03:35:02.210927	2025-12-22 03:35:02.336236	t
9729d4c9-91d8-4f2b-98f3-3eec87d04985	180	machine_a0f91e97_0	\N	1.0.0	2025-12-22 03:35:02.426945	2025-12-22 03:35:02.426948	t
3d652bc5-83f0-486f-b363-028a8543ce9b	180	machine_a0f91e97_1	\N	1.0.0	2025-12-22 03:35:02.426957	2025-12-22 03:35:02.426957	f
66e2beb4-09ca-4ba5-8c81-c20c111776ba	180	machine_a0f91e97_2	\N	1.0.0	2025-12-22 03:35:02.426964	2025-12-22 03:35:02.426965	t
1bc924fb-e184-45f5-aefc-5358d3c0542c	180	machine_a0f91e97_3	\N	1.0.0	2025-12-22 03:35:02.426971	2025-12-22 03:35:02.426972	f
e3f96740-5528-457e-aaf9-c460fd32a22b	180	machine_a0f91e97_4	\N	1.0.0	2025-12-22 03:35:02.426979	2025-12-22 03:35:02.426979	t
34495c08-3096-47b1-848c-7532c918e144	182	login_machine_8fd7da02	10.0.0.1	1.0.0	2025-12-22 03:35:02.593358	2025-12-22 03:35:02.59336	t
42154974-8ddc-4220-8d17-d2dfbbc2cab0	13	test-machine-001	127.0.0.1	1.0.0	2025-12-22 03:35:46.766196	2025-12-22 03:35:46.766197	t
aaee0789-14d2-4a9b-8670-a8273a740be0	207	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 03:35:51.022639	2025-12-22 03:35:51.022641	t
bec12b6c-ff38-4875-a2d1-6d29ff6cee25	276	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 05:25:11.302204	2025-12-22 05:25:11.302206	t
189cbabe-5834-49eb-a394-7442d31535d4	208	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 03:35:51.971552	2025-12-22 03:35:52.167539	f
75637ea5-1e83-4098-9dbf-562f90f9406b	209	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 03:35:52.534908	2025-12-22 03:35:52.534909	t
7e8f7394-2ef2-48a1-882b-6e72c5ba68d0	209	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 03:35:52.535015	2025-12-22 03:35:52.535016	t
e215b4d0-55df-40a1-b4f7-a5be993a1b74	209	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 03:35:52.535071	2025-12-22 03:35:52.535071	f
525a4dce-3099-4f66-b815-df6a839b3294	213	test_machine_af9165c1	192.168.1.100	2512010029	2025-12-22 03:35:53.285313	2025-12-22 03:35:53.285315	t
92b15420-497e-4dd5-b8c4-ab4245859dc8	214	machine_4670bc3a_0	\N	1.0.0	2025-12-22 03:35:53.376968	2025-12-22 03:35:53.37697	t
27425c55-c534-417b-bdde-0de94cd9c86d	214	machine_4670bc3a_1	\N	1.0.0	2025-12-22 03:35:53.376981	2025-12-22 03:35:53.376981	t
1ee7fc59-2e7f-4dd4-be47-2154cdd1375c	214	machine_4670bc3a_2	\N	1.0.0	2025-12-22 03:35:53.376989	2025-12-22 03:35:53.37699	t
64b3fa3a-b0fc-4934-ba0b-9bfa6118f161	215	machine_80cf8d57	\N	1.0.0	2025-12-22 03:35:53.468319	2025-12-22 03:35:53.494327	f
fd060d99-f976-4494-8326-13d33cb5b38b	216	machine_6f47d8f9	\N	1.0.0	2025-12-22 03:35:53.586713	2025-12-22 03:35:53.715968	t
9590aaf4-1961-45be-bd9c-2474deb137ee	217	machine_baae9a66_0	\N	1.0.0	2025-12-22 03:35:53.881582	2025-12-22 03:35:53.881584	t
c244fde4-2aba-4e32-8edf-bfd04cfd5ae3	217	machine_baae9a66_1	\N	1.0.0	2025-12-22 03:35:53.881594	2025-12-22 03:35:53.881594	f
decb3b5a-76d9-427e-8186-f639e88bb286	217	machine_baae9a66_2	\N	1.0.0	2025-12-22 03:35:53.881602	2025-12-22 03:35:53.881603	t
c2b10182-40a3-4fa2-9a34-bdbc5ea7b3d5	217	machine_baae9a66_3	\N	1.0.0	2025-12-22 03:35:53.88161	2025-12-22 03:35:53.88161	f
dde09d44-943d-45ff-a94d-ec2e341d8596	217	machine_baae9a66_4	\N	1.0.0	2025-12-22 03:35:53.881617	2025-12-22 03:35:53.881618	t
0fdde700-b1d5-4fc4-945d-bf26d3dd3c02	219	login_machine_17ec779c	10.0.0.1	1.0.0	2025-12-22 03:35:54.156508	2025-12-22 03:35:54.156509	t
c339edc1-3600-434e-81e6-44f160a72a1e	244	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:02:40.299365	2025-12-22 05:02:40.299367	t
8380c014-b479-4d0a-8530-673ac5e1a649	260	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:03:23.088484	2025-12-22 05:03:23.142215	f
4d7eaee6-173c-44d0-9e3a-9aadda2ffebb	245	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:02:40.677853	2025-12-22 05:02:40.75053	f
e11d39f5-9d5e-4387-8fb8-246dc2c7dd2b	246	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 05:02:41.099622	2025-12-22 05:02:41.099624	t
a407ebab-fa8c-434e-86b6-62b4d95c1718	246	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:02:41.099726	2025-12-22 05:02:41.099727	t
e1c0b4b1-9cc3-4965-a973-8b807585bb5f	246	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:02:41.09978	2025-12-22 05:02:41.09978	f
ad3545ba-3367-40dc-9676-7364705b6aea	259	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:03:22.726435	2025-12-22 05:03:22.726438	t
caf53b18-a85c-43b2-b66e-953e2efb4cc3	261	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 05:03:23.445661	2025-12-22 05:03:23.445663	t
33457b56-7eba-4621-b3ea-402bd62a145e	261	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:03:23.445759	2025-12-22 05:03:23.445759	t
defa808c-4a15-4404-b618-20f27ccf9bb2	261	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:03:23.445811	2025-12-22 05:03:23.445811	f
26d5a68b-ce0d-4927-9543-f3232e3e9cf9	13	test-machine-001	127.0.0.1	1.0.0	2025-12-22 05:25:14.904113	2025-12-22 05:25:14.904114	t
4b625bf2-189f-4e55-b8eb-0b17409f6915	274	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:25:10.924607	2025-12-22 05:25:10.924609	t
6457d630-99d5-4009-98cd-ab88e98b9990	275	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:25:10.798935	2025-12-22 05:25:10.92601	f
3b564e54-2f4c-4a17-9df7-42cab9ec5d2b	276	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:25:11.302305	2025-12-22 05:25:11.302305	t
d3714981-3840-41c6-b716-aaaef4ebd428	276	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:25:11.302358	2025-12-22 05:25:11.302359	f
ecf44039-fb08-4c63-ac79-ad0c2d52bc41	280	test_machine_f09043b8	192.168.1.100	2512010029	2025-12-22 05:25:12.136021	2025-12-22 05:25:12.136023	t
949cc42d-00ff-468d-8d4b-aa2956e78971	281	machine_2e3b65bb_0	\N	1.0.0	2025-12-22 05:25:12.23601	2025-12-22 05:25:12.236013	t
5ab56dcf-86dd-4409-8338-a19e4663f091	281	machine_2e3b65bb_1	\N	1.0.0	2025-12-22 05:25:12.236023	2025-12-22 05:25:12.236024	t
5a99444e-3549-43f2-81bd-d2657e18553e	281	machine_2e3b65bb_2	\N	1.0.0	2025-12-22 05:25:12.236032	2025-12-22 05:25:12.236032	t
c3e57bf9-0da0-4b69-a41c-56fa66171eba	282	machine_7258ae07	\N	1.0.0	2025-12-22 05:25:12.327875	2025-12-22 05:25:12.3643	f
3ae5957c-9d39-41f4-8654-6541cd909e88	283	machine_ea5d8ac3	\N	1.0.0	2025-12-22 05:25:12.456923	2025-12-22 05:25:12.5875	t
2a418e65-f2d4-4e5d-b89a-57715255493e	284	machine_87b63827_0	\N	1.0.0	2025-12-22 05:25:12.694602	2025-12-22 05:25:12.694604	t
8bfa801f-a10e-46bb-b0aa-4342203ab2b6	284	machine_87b63827_1	\N	1.0.0	2025-12-22 05:25:12.694614	2025-12-22 05:25:12.694615	f
8e578d7a-5511-42af-accc-7ecc4c6d30ff	284	machine_87b63827_2	\N	1.0.0	2025-12-22 05:25:12.694622	2025-12-22 05:25:12.694623	t
f3c96028-b425-488d-9c77-e2f31654a6f4	284	machine_87b63827_3	\N	1.0.0	2025-12-22 05:25:12.694629	2025-12-22 05:25:12.69463	f
1322087f-6f3b-4c49-833d-73a13d06a7c0	284	machine_87b63827_4	\N	1.0.0	2025-12-22 05:25:12.694636	2025-12-22 05:25:12.694637	t
18cf30d7-fe11-47a1-b2ed-54925c777f74	286	login_machine_1de021e4	10.0.0.1	1.0.0	2025-12-22 05:25:12.879105	2025-12-22 05:25:12.879106	t
a5ed2fe8-004b-4405-98c5-0f69e4e13309	13	test-machine-001	127.0.0.1	1.0.0	2025-12-22 05:29:43.245725	2025-12-22 05:29:43.245726	t
c6a79acf-95fd-4207-abf8-2172ca45ea69	311	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:29:47.99917	2025-12-22 05:29:47.999172	t
e3607876-8ad5-4a41-8db0-5af4c18f6dbc	386	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:50:14.161054	2025-12-22 05:50:14.351698	f
69cec0e8-5e07-4d4b-b28c-ce99c028333b	312	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:29:48.448913	2025-12-22 05:29:48.520656	f
5bc67fd8-6fba-4695-9f74-82ff0577be8a	313	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 05:29:48.843044	2025-12-22 05:29:48.843047	t
1a01873a-06d7-467b-a574-22f57651fb45	313	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:29:48.843155	2025-12-22 05:29:48.843155	t
3c1dd8e8-92ca-450b-ae46-072bca22d45f	313	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:29:48.84321	2025-12-22 05:29:48.843211	f
a2a07470-f53d-4673-9c11-44279afa0b19	317	test_machine_dc897876	192.168.1.100	2512010029	2025-12-22 05:29:49.639663	2025-12-22 05:29:49.639666	t
df186944-e7f0-4983-879f-1fc1ae4c7ae7	318	machine_ba547928_0	\N	1.0.0	2025-12-22 05:29:49.832249	2025-12-22 05:29:49.832252	t
98ee23f6-75dd-455f-8f77-fb3ebcfe104f	318	machine_ba547928_1	\N	1.0.0	2025-12-22 05:29:49.832262	2025-12-22 05:29:49.832263	t
c27c236c-0bb7-4496-9f39-38aff144657e	318	machine_ba547928_2	\N	1.0.0	2025-12-22 05:29:49.83227	2025-12-22 05:29:49.832271	t
9cc35bda-76e7-441f-a11d-060c55b45b37	319	machine_bea0aab7	\N	1.0.0	2025-12-22 05:29:49.96398	2025-12-22 05:29:49.995893	f
ae96159c-6979-4b25-b78e-90043b02dd4c	320	machine_454f3297	\N	1.0.0	2025-12-22 05:29:50.189213	2025-12-22 05:29:50.410378	t
4083d3a5-40a1-4626-a08b-030b2f9c1010	321	machine_f611748f_0	\N	1.0.0	2025-12-22 05:29:50.528967	2025-12-22 05:29:50.52897	t
6cc38da8-79cb-40c2-93fb-a7d545c1b912	321	machine_f611748f_1	\N	1.0.0	2025-12-22 05:29:50.528979	2025-12-22 05:29:50.52898	f
78b4a435-ff68-41b5-afbc-d53816ed5cb3	321	machine_f611748f_2	\N	1.0.0	2025-12-22 05:29:50.528987	2025-12-22 05:29:50.528988	t
4c74da7e-6bc3-4daf-a72f-b133b40058e7	321	machine_f611748f_3	\N	1.0.0	2025-12-22 05:29:50.528994	2025-12-22 05:29:50.528995	f
1ef2321e-7fce-4c8a-ae5b-48077e52129e	321	machine_f611748f_4	\N	1.0.0	2025-12-22 05:29:50.529001	2025-12-22 05:29:50.529002	t
4e9e97cd-5294-46fb-99a3-962d07b1d8f1	323	login_machine_a5c73a45	10.0.0.1	1.0.0	2025-12-22 05:29:50.731562	2025-12-22 05:29:50.731563	t
45731d8a-dbe5-4bc8-85e2-9ccf5d8dfc91	13	test-machine-001	127.0.0.1	1.0.0	2025-12-22 05:31:50.967757	2025-12-22 05:31:50.967758	t
83be3028-16ea-4a7e-87a0-f3680d9cf3ba	348	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:31:55.277699	2025-12-22 05:31:55.277701	t
6b6f45c4-b91f-4c3e-8e07-6324c5cd50ec	387	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 05:50:14.737927	2025-12-22 05:50:14.737929	t
ef826162-0c71-4c82-98df-715468b547ac	349	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:31:55.699789	2025-12-22 05:31:55.854643	f
bcbe878e-b7cd-469b-ac8b-a5aa6eaeacf8	350	test-machine-000	127.0.0.1	1.0.0-test	2025-12-22 05:31:56.249334	2025-12-22 05:31:56.249336	t
c2ed9eb2-08dc-4985-bec2-88d1abfd90ca	350	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:31:56.249439	2025-12-22 05:31:56.249439	t
fa2b59ca-7acd-45ed-96af-e39f16bd4f98	350	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:31:56.249496	2025-12-22 05:31:56.249496	f
1ae5bd83-2d6d-4e68-8f82-3c986e63dfdc	354	test_machine_7c39a66a	192.168.1.100	2512010029	2025-12-22 05:31:56.564952	2025-12-22 05:31:56.564955	t
2e6bca4d-1146-4bcb-a51c-5f9191f95de1	355	machine_c75f77d0_0	\N	1.0.0	2025-12-22 05:31:56.711952	2025-12-22 05:31:56.711955	t
487c7188-620c-41b8-9dab-cf2e8d97ea64	355	machine_c75f77d0_1	\N	1.0.0	2025-12-22 05:31:56.711964	2025-12-22 05:31:56.711965	t
516fddec-1a31-4b99-935e-4d1f0f264b11	355	machine_c75f77d0_2	\N	1.0.0	2025-12-22 05:31:56.711973	2025-12-22 05:31:56.711974	t
2fe620e9-621b-4ac5-8d9a-ac44e667436d	356	machine_588a9e3f	\N	1.0.0	2025-12-22 05:31:57.130084	2025-12-22 05:31:57.178317	f
e1c09585-948c-4744-8d00-cfb47cf47f1c	357	machine_85fc9608	\N	1.0.0	2025-12-22 05:31:57.414633	2025-12-22 05:31:57.608487	t
b861e3e3-32d8-483d-8986-7a22b5586d09	358	machine_df175393_0	\N	1.0.0	2025-12-22 05:31:57.784496	2025-12-22 05:31:57.784499	t
f55125b1-eba9-4920-9f16-13734971ff8c	358	machine_df175393_1	\N	1.0.0	2025-12-22 05:31:57.784508	2025-12-22 05:31:57.784509	f
dcfdfa1b-5599-4b7b-a328-135d5b914980	358	machine_df175393_2	\N	1.0.0	2025-12-22 05:31:57.784533	2025-12-22 05:31:57.784534	t
949a138e-0e63-46fd-968a-96e8e93a5d0f	358	machine_df175393_3	\N	1.0.0	2025-12-22 05:31:57.784543	2025-12-22 05:31:57.784544	f
13e4c820-8411-4ad3-a821-d5a8416c7962	358	machine_df175393_4	\N	1.0.0	2025-12-22 05:31:57.784551	2025-12-22 05:31:57.784552	t
01b95c3d-45dd-4fe1-8926-3fb959ede26f	360	login_machine_b309966a	10.0.0.1	1.0.0	2025-12-22 05:31:58.139509	2025-12-22 05:31:58.139511	t
a7efd6c5-212e-4c36-9c36-dee32712667b	13	test-machine-001	127.0.0.1	1.0.0	2025-12-22 05:50:09.282949	2025-12-22 05:50:09.28295	t
6a016de8-cc24-4e1c-bedb-764f92c1b44e	385	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:50:13.492249	2025-12-22 05:50:13.492251	t
2bf6342c-8eb7-416f-b37e-323deedb5a66	393	machine_644a7736	\N	1.0.0	2025-12-22 05:50:15.965774	2025-12-22 05:50:16.005659	f
2779bd1d-93cb-43c2-9e66-300da07afa1b	387	test-machine-001	127.0.0.1	1.0.0-test	2025-12-22 05:50:14.738029	2025-12-22 05:50:14.738029	t
d2e3faac-bd97-4e15-8186-88891e601a91	387	test-machine-002	127.0.0.1	1.0.0-test	2025-12-22 05:50:14.738084	2025-12-22 05:50:14.738085	f
1aa9b0a5-9a36-4e96-a302-6d596cd8ccf8	391	test_machine_1ddb3810	192.168.1.100	2512010029	2025-12-22 05:50:15.599189	2025-12-22 05:50:15.599192	t
74f31280-b8fb-4800-9ebe-a2b34fcb6484	392	machine_f901d8d0_0	\N	1.0.0	2025-12-22 05:50:15.773637	2025-12-22 05:50:15.77364	t
5d0962bb-72a8-4195-9734-0579a89cec5f	392	machine_f901d8d0_1	\N	1.0.0	2025-12-22 05:50:15.773673	2025-12-22 05:50:15.773674	t
c40c0034-6fe2-4996-b4ee-ee39a88cf467	392	machine_f901d8d0_2	\N	1.0.0	2025-12-22 05:50:15.773683	2025-12-22 05:50:15.773684	t
be951420-5235-46ff-a0d7-d2677e0b5b8d	394	machine_4e7b6da3	\N	1.0.0	2025-12-22 05:50:16.110988	2025-12-22 05:50:16.243859	t
42438d44-dc10-40e8-903e-38a44d2c6e20	395	machine_5b83e03e_0	\N	1.0.0	2025-12-22 05:50:16.34198	2025-12-22 05:50:16.341982	t
927af588-3da3-4ce4-8ead-69e6c4442677	395	machine_5b83e03e_1	\N	1.0.0	2025-12-22 05:50:16.341992	2025-12-22 05:50:16.341993	f
b67e2149-0d67-4024-a152-b6f2cee12887	395	machine_5b83e03e_2	\N	1.0.0	2025-12-22 05:50:16.342	2025-12-22 05:50:16.342001	t
ffd68339-2766-4fe9-880e-62fc662e3bef	395	machine_5b83e03e_3	\N	1.0.0	2025-12-22 05:50:16.342007	2025-12-22 05:50:16.342008	f
b2855cf2-93cb-4380-a38d-fc231cbd6c54	395	machine_5b83e03e_4	\N	1.0.0	2025-12-22 05:50:16.342015	2025-12-22 05:50:16.342015	t
42975d6c-87fc-45d4-9da7-34e29e701f7f	397	login_machine_cf5004c6	10.0.0.1	1.0.0	2025-12-22 05:50:16.525918	2025-12-22 05:50:16.52592	t
3d02a848-e35f-4645-90d4-39d36e06ada2	432	test-machine-001	127.0.0.1	1.0.0-test	2025-12-27 16:35:53.218235	2025-12-27 16:35:53.218237	t
045020e8-6c0d-4530-8c88-bae7091fb6a8	433	test-machine-002	127.0.0.1	1.0.0-test	2025-12-27 16:35:53.828368	2025-12-27 16:35:53.879576	f
c9acc9d1-6163-45d5-a718-e46df4a15c61	434	test-machine-000	127.0.0.1	1.0.0-test	2025-12-27 16:35:54.164393	2025-12-27 16:35:54.164395	t
23f95e48-ce67-4518-977a-db513f4a7d58	434	test-machine-001	127.0.0.1	1.0.0-test	2025-12-27 16:35:54.16447	2025-12-27 16:35:54.16447	t
d7e0c0c8-d899-42fa-9784-a7c69c99c9c0	434	test-machine-002	127.0.0.1	1.0.0-test	2025-12-27 16:35:54.164501	2025-12-27 16:35:54.164501	f
977347a3-e69f-40bc-913f-ea1e1ccab066	438	test_machine_92e94202	192.168.1.100	2512010029	2025-12-27 16:35:54.820026	2025-12-27 16:35:54.820028	t
1501b123-7dab-432f-b172-47eccafedaed	439	machine_06f876f6_0	\N	1.0.0	2025-12-27 16:35:54.901304	2025-12-27 16:35:54.901306	t
48cc530b-d20c-4ae7-b4d4-58d51a83b97a	439	machine_06f876f6_1	\N	1.0.0	2025-12-27 16:35:54.901311	2025-12-27 16:35:54.901311	t
487482df-46c9-4f63-b5fd-d777355079f6	439	machine_06f876f6_2	\N	1.0.0	2025-12-27 16:35:54.901315	2025-12-27 16:35:54.901315	t
d58c030b-c8f6-44a3-95c8-c74930764837	440	machine_23f68fc9	\N	1.0.0	2025-12-27 16:35:54.985755	2025-12-27 16:35:55.008912	f
6da8f095-b623-48ca-a448-cc565242d272	441	machine_5c36fecc	\N	1.0.0	2025-12-27 16:35:55.086557	2025-12-27 16:35:55.209274	t
1e352c74-dc4e-4ea6-a9cb-660515d8f9dd	442	machine_3842799c_0	\N	1.0.0	2025-12-27 16:35:55.281602	2025-12-27 16:35:55.281604	t
b6472c79-972a-476e-9b57-19274578ddbb	442	machine_3842799c_1	\N	1.0.0	2025-12-27 16:35:55.281609	2025-12-27 16:35:55.281609	f
62e713f4-0948-46be-ac2c-80574b703336	442	machine_3842799c_2	\N	1.0.0	2025-12-27 16:35:55.281613	2025-12-27 16:35:55.281613	t
b9e2869c-9806-46cd-841e-4997c0ba3e67	442	machine_3842799c_3	\N	1.0.0	2025-12-27 16:35:55.281616	2025-12-27 16:35:55.281617	f
3c6aeaf2-f126-49ba-935c-360f648340a6	442	machine_3842799c_4	\N	1.0.0	2025-12-27 16:35:55.28162	2025-12-27 16:35:55.28162	t
102d973f-e8a2-4714-83da-00a700227460	444	login_machine_89978d33	10.0.0.1	1.0.0	2025-12-27 16:35:55.439465	2025-12-27 16:35:55.439467	t
67d88ddb-5312-4cc1-9dfd-99cf76197a42	13	test-machine-001	127.0.0.1	1.0.0	2025-12-28 08:30:07.032787	2025-12-28 08:30:07.032789	t
596beb67-cecd-44c9-9e72-f0c7accccad6	13	test-machine-001	127.0.0.1	1.0.0	2025-12-28 08:32:01.603237	2025-12-28 08:32:01.60324	t
21795338-ba96-431e-887f-6566ce629cc1	469	test-machine-001	127.0.0.1	1.0.0-test	2025-12-28 08:32:06.350798	2025-12-28 08:32:06.3508	t
73c642b4-106c-429d-99e7-e1c01726fca0	521	machine_554275a2	\N	1.0.0	2026-01-12 13:04:17.021533	2026-01-12 13:04:17.047319	f
6ee2d6cf-f0a6-42a6-acb2-9bc43d650e73	470	test-machine-002	127.0.0.1	1.0.0-test	2025-12-28 08:32:06.72241	2025-12-28 08:32:06.82113	f
07e55671-220d-4459-a19e-144ecd68cf64	471	test-machine-000	127.0.0.1	1.0.0-test	2025-12-28 08:32:07.121203	2025-12-28 08:32:07.121205	t
e57e0ed9-8c78-40b2-bc17-abf81eb00c2a	471	test-machine-001	127.0.0.1	1.0.0-test	2025-12-28 08:32:07.121282	2025-12-28 08:32:07.121282	t
da18988d-503c-4331-8ee4-307b3a5c237b	471	test-machine-002	127.0.0.1	1.0.0-test	2025-12-28 08:32:07.121313	2025-12-28 08:32:07.121313	f
e21d4548-4383-4f83-8824-014a994b6599	475	test_machine_de458697	192.168.1.100	2512010029	2025-12-28 08:32:05.138303	2025-12-28 08:32:05.138306	t
90676850-ba34-4139-be51-13f84cf2d53f	476	machine_ab2c201d_0	\N	1.0.0	2025-12-28 08:32:05.229424	2025-12-28 08:32:05.229426	t
312f1f76-308c-4c5f-a426-b1887143b7d9	476	machine_ab2c201d_1	\N	1.0.0	2025-12-28 08:32:05.229432	2025-12-28 08:32:05.229432	t
1fa07efc-9500-4370-922c-6bae87a9b875	476	machine_ab2c201d_2	\N	1.0.0	2025-12-28 08:32:05.229436	2025-12-28 08:32:05.229436	t
0ac3648f-3aa2-4fab-81cd-199f01e63a20	477	machine_365466d9	\N	1.0.0	2025-12-28 08:32:05.319536	2025-12-28 08:32:05.348587	f
234efec2-1027-4e51-b8f8-32941914fefe	478	machine_095ce308	\N	1.0.0	2025-12-28 08:32:05.430406	2025-12-28 08:32:05.559582	t
1ea1cf2b-308d-4fd8-91e3-32eb3e72aead	479	machine_47a63ca7_0	\N	1.0.0	2025-12-28 08:32:05.646004	2025-12-28 08:32:05.646007	t
85a4085e-3b84-4bc3-9a0d-c72a3724ad38	479	machine_47a63ca7_1	\N	1.0.0	2025-12-28 08:32:05.646014	2025-12-28 08:32:05.646014	f
7d9b6182-b32b-4694-a592-cde8bbdf9fad	479	machine_47a63ca7_2	\N	1.0.0	2025-12-28 08:32:05.646018	2025-12-28 08:32:05.646018	t
aac86eec-4af3-4c36-bbd4-489a2298dc1c	479	machine_47a63ca7_3	\N	1.0.0	2025-12-28 08:32:05.646021	2025-12-28 08:32:05.646021	f
66b8ec53-6df4-43c2-9640-ed7877ac6789	479	machine_47a63ca7_4	\N	1.0.0	2025-12-28 08:32:05.646024	2025-12-28 08:32:05.646025	t
f78d2698-3c65-48a1-b108-ee8cbaaa1bec	481	login_machine_8fb19523	10.0.0.1	1.0.0	2025-12-28 08:32:05.818944	2025-12-28 08:32:05.818946	t
e48c2cc3-437a-488d-acf5-c76f031a5e09	13	test-machine-001	127.0.0.1	1.0.0	2025-12-28 08:32:28.431201	2025-12-28 08:32:28.431202	t
6f9447c2-65a0-42ff-b91e-a2bd2dcc2509	13	test-machine-001	127.0.0.1	1.0.0	2025-12-28 09:04:03.490627	2025-12-28 09:04:03.49063	t
eae8ba2d-f540-4257-83e7-39610974e572	13	test-machine-001	127.0.0.1	1.0.0	2026-01-12 13:04:11.055364	2026-01-12 13:04:11.055366	t
2242e954-5f2a-4405-b82b-f40f16558f2c	513	test-machine-001	127.0.0.1	1.0.0-test	2026-01-12 13:04:15.272373	2026-01-12 13:04:15.272374	t
715d10e8-8ed8-4755-9319-6b026c285f82	514	test-machine-002	127.0.0.1	1.0.0-test	2026-01-12 13:04:15.657751	2026-01-12 13:04:15.75424	f
5a0600e4-5f04-4290-bec5-1fe27112434f	515	test-machine-000	127.0.0.1	1.0.0-test	2026-01-12 13:04:16.03843	2026-01-12 13:04:16.038432	t
d3b4bd6a-2f4c-4868-bd22-e03fac5e6cab	515	test-machine-001	127.0.0.1	1.0.0-test	2026-01-12 13:04:16.038545	2026-01-12 13:04:16.038546	t
7741aa25-2485-4773-9e0c-5a7732886c05	515	test-machine-002	127.0.0.1	1.0.0-test	2026-01-12 13:04:16.038595	2026-01-12 13:04:16.038595	f
cf7207f1-9db8-4fe8-8f73-c14fa6d4ddb7	519	test_machine_4270b3c3	192.168.1.100	2512010029	2026-01-12 13:04:16.75405	2026-01-12 13:04:16.754053	t
df10b1f9-9bae-4cb9-944c-81d247dfdfc7	520	machine_efc8d37a_0	\N	1.0.0	2026-01-12 13:04:16.837879	2026-01-12 13:04:16.837881	t
9c5ada67-703c-487d-a29c-b626801862ce	520	machine_efc8d37a_1	\N	1.0.0	2026-01-12 13:04:16.83789	2026-01-12 13:04:16.837891	t
4b764d94-9229-4a40-98a9-71fb8f9fec1a	520	machine_efc8d37a_2	\N	1.0.0	2026-01-12 13:04:16.837897	2026-01-12 13:04:16.837898	t
5cb02e16-3eb8-4c4f-aed0-e563455864bd	522	machine_ea339a44	\N	1.0.0	2026-01-12 13:04:17.131244	2026-01-12 13:04:17.253496	t
1c2f7e0b-6501-4611-b2bc-f8eabd4bf43e	523	machine_f97ebc07_0	\N	1.0.0	2026-01-12 13:04:17.338215	2026-01-12 13:04:17.338217	t
9b29dbfe-9945-4b78-8800-c946fec68d29	523	machine_f97ebc07_1	\N	1.0.0	2026-01-12 13:04:17.338225	2026-01-12 13:04:17.338226	f
e2f3a1b8-25df-4e57-9862-1bdaa22096d5	523	machine_f97ebc07_2	\N	1.0.0	2026-01-12 13:04:17.338232	2026-01-12 13:04:17.338233	t
4f5a9be4-654e-4f08-b5d0-b7c7748f58b0	523	machine_f97ebc07_3	\N	1.0.0	2026-01-12 13:04:17.338239	2026-01-12 13:04:17.338239	f
620ce160-ae46-42b1-8a71-d38a07485acf	523	machine_f97ebc07_4	\N	1.0.0	2026-01-12 13:04:17.338245	2026-01-12 13:04:17.338246	t
32adf573-0297-44e1-892e-4926f88610c6	525	login_machine_df69fc34	10.0.0.1	1.0.0	2026-01-12 13:04:17.506044	2026-01-12 13:04:17.506045	t
5f6fde8a-cfee-446e-89a2-0e0ce4373696	13	test-machine-001	127.0.0.1	1.0.0	2026-01-13 16:23:00.775807	2026-01-13 16:23:00.775809	t
29a98b7c-d7fa-4d62-a110-c176c98cfa86	550	test-machine-001	127.0.0.1	1.0.0-test	2026-01-13 16:23:02.757967	2026-01-13 16:23:02.75797	t
eb9a45b6-7acd-4aa9-bf9e-b4fe22e0b082	552	test-machine-000	127.0.0.1	1.0.0-test	2026-01-13 16:23:03.542519	2026-01-13 16:23:03.542522	t
5facd11a-dd44-40d1-a49d-f81b8cc07d50	551	test-machine-002	127.0.0.1	1.0.0-test	2026-01-13 16:23:03.120363	2026-01-13 16:23:03.182453	f
78ac826e-e251-476b-8f4b-8b88d55fa0f0	552	test-machine-001	127.0.0.1	1.0.0-test	2026-01-13 16:23:03.542614	2026-01-13 16:23:03.542614	t
d4072a0d-94a0-4661-a72a-7b55f519cf16	552	test-machine-002	127.0.0.1	1.0.0-test	2026-01-13 16:23:03.542666	2026-01-13 16:23:03.542666	f
2eddf084-985c-4167-87ec-480a8c1c7d11	556	test_machine_b96820a6	192.168.1.100	2512010029	2026-01-13 16:23:04.365859	2026-01-13 16:23:04.365861	t
9db3d609-f422-49b7-af7c-334a51736339	557	machine_2039cdf5_0	\N	1.0.0	2026-01-13 16:23:04.45625	2026-01-13 16:23:04.456252	t
a0ec1cf4-9500-4386-934b-6319b9ae31a9	557	machine_2039cdf5_1	\N	1.0.0	2026-01-13 16:23:04.456262	2026-01-13 16:23:04.456263	t
878a3603-afca-481f-a80d-52cbae3ae921	557	machine_2039cdf5_2	\N	1.0.0	2026-01-13 16:23:04.456271	2026-01-13 16:23:04.456272	t
b207be38-5f25-4fc6-a97d-fa39cf10202a	558	machine_333e944c	\N	1.0.0	2026-01-13 16:23:04.546819	2026-01-13 16:23:04.575316	f
b26e0c01-29f4-4cf9-90c9-b40cf7f01664	559	machine_affde55e	\N	1.0.0	2026-01-13 16:23:04.66671	2026-01-13 16:23:04.795139	t
d1ce37a4-6e5d-46ce-8eb9-8673df953f80	560	machine_a7cc1195_0	\N	1.0.0	2026-01-13 16:23:04.891097	2026-01-13 16:23:04.891099	t
0bb9f090-2e52-4d66-8351-f4f927484775	560	machine_a7cc1195_1	\N	1.0.0	2026-01-13 16:23:04.891149	2026-01-13 16:23:04.89115	f
1cd097d0-df3a-4d12-9796-c9d5ad2025c7	560	machine_a7cc1195_2	\N	1.0.0	2026-01-13 16:23:04.891186	2026-01-13 16:23:04.891187	t
15f1cf9c-6b49-4b22-bdae-6d0325020e87	560	machine_a7cc1195_3	\N	1.0.0	2026-01-13 16:23:04.891212	2026-01-13 16:23:04.891213	f
6797822e-68f3-4604-a695-d101a044dce7	560	machine_a7cc1195_4	\N	1.0.0	2026-01-13 16:23:04.89122	2026-01-13 16:23:04.89124	t
7a189f4a-2916-4a69-ad57-3f27153c7a1d	562	login_machine_d13a9f77	10.0.0.1	1.0.0	2026-01-13 16:23:05.073383	2026-01-13 16:23:05.073384	t
7ea8567c-0ee1-4ea0-848b-ac878282eb89	13	test-machine-001	127.0.0.1	1.0.0	2026-01-14 04:13:24.154893	2026-01-14 04:13:24.154895	t
ff22a35f-eea8-4b2e-ba82-d152f26feb97	587	test-machine-001	127.0.0.1	1.0.0-test	2026-01-14 04:13:28.586875	2026-01-14 04:13:28.586877	t
278ce3bb-a712-4507-a9ee-542d6e01c25d	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:08:03.437452	2026-03-15 18:08:03.485127	f
ffe7d510-000a-4c14-be46-fb3301a89235	588	test-machine-002	127.0.0.1	1.0.0-test	2026-01-14 04:13:28.997741	2026-01-14 04:13:29.062875	f
037d2858-154b-4a73-9827-769bbcfb8a6f	589	test-machine-000	127.0.0.1	1.0.0-test	2026-01-14 04:13:29.352895	2026-01-14 04:13:29.352896	t
095759b3-7970-4bf6-9c72-63fcbd7887fe	589	test-machine-001	127.0.0.1	1.0.0-test	2026-01-14 04:13:29.352992	2026-01-14 04:13:29.352993	t
0d81ed2e-8994-469d-9fe0-d39eb1db10be	589	test-machine-002	127.0.0.1	1.0.0-test	2026-01-14 04:13:29.353041	2026-01-14 04:13:29.353041	f
0b74d3df-232f-4533-9284-b8c5da1c2f6c	593	test_machine_9e60a238	192.168.1.100	2512010029	2026-01-14 04:13:30.028254	2026-01-14 04:13:30.028257	t
37a90204-7cd1-4684-80e7-0360ce26adb0	594	machine_47142c7c_0	\N	1.0.0	2026-01-14 04:13:30.110594	2026-01-14 04:13:30.110596	t
d3bae6fc-b0a8-41a5-be0a-e1d3d55fa319	594	machine_47142c7c_1	\N	1.0.0	2026-01-14 04:13:30.110605	2026-01-14 04:13:30.110606	t
0ef226a5-4793-445e-bb80-be6ba18f11ef	594	machine_47142c7c_2	\N	1.0.0	2026-01-14 04:13:30.110614	2026-01-14 04:13:30.110614	t
5d5482b2-635e-493d-b4be-deb58ff4f4e9	595	machine_4fc05931	\N	1.0.0	2026-01-14 04:13:30.192519	2026-01-14 04:13:30.213693	f
28dbf3bc-424b-4685-81c1-158d81910128	596	machine_9a69d5fd	\N	1.0.0	2026-01-14 04:13:30.316718	2026-01-14 04:13:30.437203	t
3030503b-a484-450f-94ad-537d07e92963	597	machine_fffa6754_0	\N	1.0.0	2026-01-14 04:13:30.520781	2026-01-14 04:13:30.520783	t
f3e57b34-c516-4365-b61e-0c38d64129e2	597	machine_fffa6754_1	\N	1.0.0	2026-01-14 04:13:30.520808	2026-01-14 04:13:30.520809	f
5c113006-42ac-4b31-9a87-50d438485d9d	597	machine_fffa6754_2	\N	1.0.0	2026-01-14 04:13:30.520821	2026-01-14 04:13:30.520822	t
d78d9e2b-e7f7-400a-98d1-125b8be4784d	597	machine_fffa6754_3	\N	1.0.0	2026-01-14 04:13:30.520829	2026-01-14 04:13:30.520829	f
7b962647-b605-4b38-aeb2-b28937d2a9c7	597	machine_fffa6754_4	\N	1.0.0	2026-01-14 04:13:30.520835	2026-01-14 04:13:30.520836	t
66ecdc9b-ddf6-418b-8fd6-7d49f15bf459	599	login_machine_b12991b5	10.0.0.1	1.0.0	2026-01-14 04:13:30.694405	2026-01-14 04:13:30.694407	t
ccf23aa3-49da-4f17-b3bb-514a6bf6a91b	2	TEST_MACHINE_001	127.0.0.1	1.0.0	2026-01-31 06:26:23.721027	2026-01-31 06:26:23.721028	t
d8f70712-ba26-453f-874d-f85491c9a39e	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:08:12.682954	2026-03-15 18:08:12.682955	t
8f9ca295-7216-4c07-ba05-7ec90b83801d	2	INTEGRATION_TEST_MACHINE	127.0.0.1	1.0.0-test	2026-01-31 06:26:29.853507	2026-01-31 06:26:29.883693	f
9921bbfd-0354-46f6-97a5-632a6ae22a2c	2	MULTI_TOOL_TEST	127.0.0.1	1.0.0	2026-01-31 06:26:30.403541	2026-01-31 06:26:30.435383	f
39bb606d-5895-4f9f-a786-c7f2809aae6c	2	TEST_MACHINE_001	127.0.0.1	1.0.0	2026-01-31 08:09:24.542451	2026-01-31 08:09:24.637235	f
765603fe-cb87-4bdd-9d60-adaed9fb7032	2	INTEGRATION_TEST_MACHINE	127.0.0.1	1.0.0-test	2026-01-31 08:10:35.063306	2026-01-31 08:10:35.6338	f
a5d34347-51ae-47d4-a36b-9f2a1c8fc57c	2	MULTI_TOOL_TEST	127.0.0.1	1.0.0	2026-01-31 08:10:37.271739	2026-01-31 08:10:37.61022	f
d0281a99-1d0f-483a-b726-fde3271c6700	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:06:41.322168	2026-03-15 18:06:41.478045	f
06829cba-1a2c-4a11-9c0b-5f2d9152ed20	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:07:21.566398	2026-03-15 18:07:21.566399	t
8a950a49-29e3-4e41-8d78-85b2a5e891fe	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:07:37.604417	2026-03-15 18:07:37.604419	t
38f20ea1-fb3e-4bb0-997b-c485952834ee	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:08:20.662484	2026-03-15 18:08:20.705884	f
690ea0eb-bc5b-4387-b098-d485a157838e	2	TEST	127.0.0.1	3.0	2026-03-15 18:07:47.797654	2026-03-15 18:07:47.842834	t
0affe88b-080b-4390-abbf-f69a4ed6350c	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:08:40.466221	2026-03-15 18:08:40.466222	t
3d2f8986-550b-449c-8a56-4e78895323d0	2	TEST-API	127.0.0.1	3.0.0	2026-03-15 18:08:48.82946	2026-03-15 18:08:48.829461	t
8529c239-c8b5-4a34-af2e-6c8ddb1d4609	2	TEST	127.0.0.1	3.0	2026-03-15 18:08:58.110519	2026-03-15 18:08:58.143739	t
baf6cd18-e6fa-4327-bb6e-247b526ac392	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 01:08:44.996224	2026-03-16 01:08:44.996226	t
becaf6dd-469b-425c-aa7d-f6f138ce99a6	642	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:08:47.620358	2026-03-16 01:08:47.62036	t
ebca9fa2-7800-4779-8ea2-1932f59d7710	648	test_machine_1217296a	192.168.1.100	2512010029	2026-03-16 01:08:49.05498	2026-03-16 01:08:49.054982	t
d2eae184-a598-4d74-b982-caea2ce6b995	643	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:08:47.993261	2026-03-16 01:08:48.054344	f
1fb927ab-2993-4504-9e33-ccc2b22828bf	644	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 01:08:48.360233	2026-03-16 01:08:48.360235	t
286866d1-c77f-448b-bf33-d17e1bfabc4a	644	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:08:48.36035	2026-03-16 01:08:48.36035	t
45e69b1d-daff-43c1-b6e5-ad78eed5fb4c	644	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:08:48.360406	2026-03-16 01:08:48.360406	f
beed575e-2118-421e-9479-cf429328e88d	649	machine_7822dbc6_0	\N	1.0.0	2026-03-16 01:08:49.178739	2026-03-16 01:08:49.178742	t
01f19e6f-8257-4848-a474-7ad0241ca0c7	649	machine_7822dbc6_1	\N	1.0.0	2026-03-16 01:08:49.178752	2026-03-16 01:08:49.178753	t
a6e3ff44-ef66-4cdd-9817-15df8b0e6c37	649	machine_7822dbc6_2	\N	1.0.0	2026-03-16 01:08:49.178761	2026-03-16 01:08:49.178761	t
a7a8d25a-7d8a-42cc-a308-d32af33cddb5	650	machine_116814f8	\N	1.0.0	2026-03-16 01:08:49.267966	2026-03-16 01:08:49.29617	f
d01c90fc-b92c-43bd-836f-0fe1ac45889f	651	machine_98af5ea5	\N	1.0.0	2026-03-16 01:08:49.386068	2026-03-16 01:08:49.510554	t
28ee5b0d-6aaa-4ae5-b38a-07b921e32d2f	652	machine_d778e6ab_0	\N	1.0.0	2026-03-16 01:08:49.607706	2026-03-16 01:08:49.607709	t
6275b034-278b-4854-af91-7e624ac3908a	652	machine_d778e6ab_1	\N	1.0.0	2026-03-16 01:08:49.607718	2026-03-16 01:08:49.607718	f
4b81a0a6-0846-4ecb-ae2e-cc912ccf547e	652	machine_d778e6ab_2	\N	1.0.0	2026-03-16 01:08:49.607725	2026-03-16 01:08:49.607726	t
a3276b81-3686-4e51-8f79-a67a909af01a	652	machine_d778e6ab_3	\N	1.0.0	2026-03-16 01:08:49.607732	2026-03-16 01:08:49.607733	f
6ab0b384-b327-44c2-9e35-b65fb10731bb	652	machine_d778e6ab_4	\N	1.0.0	2026-03-16 01:08:49.607739	2026-03-16 01:08:49.60774	t
2190d45d-7ebc-43a4-a938-ccf258a8a356	654	login_machine_9860cf80	10.0.0.1	1.0.0	2026-03-16 01:08:49.841141	2026-03-16 01:08:49.841142	t
ec946aae-e01a-482d-a40a-82b8156873b5	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 01:10:18.12605	2026-03-16 01:10:18.126052	t
fdf78fa7-1903-4615-b210-41b31cec3932	679	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:10:22.515755	2026-03-16 01:10:22.515757	t
9f41f937-575f-42ee-8ebe-7104ec420580	760	machine_2592fc81_0	\N	1.0.0	2026-03-16 01:31:49.756895	2026-03-16 01:31:49.756898	t
9f5ee11c-fe6f-4579-bd3b-54419ac2dd05	680	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:10:22.870447	2026-03-16 01:10:22.921838	f
89e5f07f-185a-4159-94c8-763032f77d6f	681	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 01:10:23.207471	2026-03-16 01:10:23.207473	t
62d9bf28-82d7-43fd-91e5-d0ecba087ca8	681	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:10:23.20757	2026-03-16 01:10:23.207571	t
2bc66f9c-70d0-41f7-8911-749361d18b04	681	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:10:23.207623	2026-03-16 01:10:23.207623	f
5044d3b1-39a3-4f8a-b11d-6393849d5b55	685	test_machine_316fce07	192.168.1.100	2512010029	2026-03-16 01:10:23.873152	2026-03-16 01:10:23.873154	t
96540d72-7695-4e84-be80-b091e0ce3016	686	machine_f45c8596_0	\N	1.0.0	2026-03-16 01:10:23.944105	2026-03-16 01:10:23.944107	t
c64d0950-ed83-47b9-9d83-c5576b9a9f57	686	machine_f45c8596_1	\N	1.0.0	2026-03-16 01:10:23.944117	2026-03-16 01:10:23.944118	t
a03d0166-c78a-45dd-99db-8e015afb1cc5	686	machine_f45c8596_2	\N	1.0.0	2026-03-16 01:10:23.944125	2026-03-16 01:10:23.944125	t
9e346460-9d05-4b25-905b-04aefbacc150	687	machine_ca4fba1e	\N	1.0.0	2026-03-16 01:10:24.035516	2026-03-16 01:10:24.066917	f
02d96487-1a44-410d-b1d7-8aaa94628692	688	machine_d606f193	\N	1.0.0	2026-03-16 01:10:24.138908	2026-03-16 01:10:24.258427	t
4423519b-166f-4db8-9f14-2c7b54c3f76f	689	machine_ac7fabfa_0	\N	1.0.0	2026-03-16 01:10:24.334266	2026-03-16 01:10:24.334268	t
38a1dacd-389f-4b99-bdf4-5a6054c36e41	689	machine_ac7fabfa_1	\N	1.0.0	2026-03-16 01:10:24.334281	2026-03-16 01:10:24.334282	f
b567cb85-e817-4e70-9273-6972deedfdb9	689	machine_ac7fabfa_2	\N	1.0.0	2026-03-16 01:10:24.334289	2026-03-16 01:10:24.33429	t
354fe7d7-440e-48a9-90b6-be508dabb25d	689	machine_ac7fabfa_3	\N	1.0.0	2026-03-16 01:10:24.334296	2026-03-16 01:10:24.334297	f
b5c687a8-d72d-495d-bde4-772a7d55e4df	689	machine_ac7fabfa_4	\N	1.0.0	2026-03-16 01:10:24.334303	2026-03-16 01:10:24.334303	t
521f534b-6b28-4e84-8aa6-7ecda751a9fc	691	login_machine_0444bd90	10.0.0.1	1.0.0	2026-03-16 01:10:24.48665	2026-03-16 01:10:24.486652	t
ffd9b2e8-6199-4629-b449-57d76ca3f828	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 01:12:17.415257	2026-03-16 01:12:17.415259	t
5919ff26-626b-42ae-8840-91628d87bccd	716	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:12:21.837298	2026-03-16 01:12:21.8373	t
3365bbc1-0dbf-4cc6-b91a-3ac97db1308e	760	machine_2592fc81_1	\N	1.0.0	2026-03-16 01:31:49.756927	2026-03-16 01:31:49.756928	t
58358472-32be-47a6-84d9-7cc6e44935a7	717	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:12:22.191592	2026-03-16 01:12:22.244067	f
7c9e74a5-ef43-47dd-8c21-1c71c3da8551	718	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 01:12:22.569389	2026-03-16 01:12:22.56939	t
10a98c8a-a745-4a2a-bba0-419b73223604	718	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:12:22.56949	2026-03-16 01:12:22.56949	t
4c087192-488a-4c25-b307-f81e9dad080d	718	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:12:22.569541	2026-03-16 01:12:22.569541	f
88005383-a5c8-4128-ba27-d1a7dda00767	722	test_machine_30eef5ba	192.168.1.100	2512010029	2026-03-16 01:12:23.27002	2026-03-16 01:12:23.270023	t
2339c6b8-5d3f-4e21-b863-544b94f6e731	723	machine_2c2a5617_0	\N	1.0.0	2026-03-16 01:12:23.530208	2026-03-16 01:12:23.530211	t
3b15c7ac-7fed-4b97-86f1-94c23f3ff305	723	machine_2c2a5617_1	\N	1.0.0	2026-03-16 01:12:23.53022	2026-03-16 01:12:23.53022	t
c5ed498d-9ddd-4058-bee5-56d0b58a3336	723	machine_2c2a5617_2	\N	1.0.0	2026-03-16 01:12:23.530228	2026-03-16 01:12:23.530228	t
94254b2c-bfae-411d-b207-53933b969b12	724	machine_535b5d9a	\N	1.0.0	2026-03-16 01:12:23.629341	2026-03-16 01:12:23.650315	f
d4456fd0-ec3c-488e-8938-8eede0813f8e	725	machine_9279262c	\N	1.0.0	2026-03-16 01:12:23.731286	2026-03-16 01:12:23.855746	t
12beb3d4-ada6-40e9-9c57-8f6ababcac9e	726	machine_b8caba97_0	\N	1.0.0	2026-03-16 01:12:23.941147	2026-03-16 01:12:23.94115	t
48b79ea8-ab6c-42f2-8afc-283e28e743f2	726	machine_b8caba97_1	\N	1.0.0	2026-03-16 01:12:23.941158	2026-03-16 01:12:23.941159	f
237c8856-9e69-4384-8a31-3bf831614c1d	726	machine_b8caba97_2	\N	1.0.0	2026-03-16 01:12:23.941166	2026-03-16 01:12:23.941167	t
8b08201b-020a-4024-89c9-ddde1bc41740	726	machine_b8caba97_3	\N	1.0.0	2026-03-16 01:12:23.941173	2026-03-16 01:12:23.941174	f
a47908f0-c9c4-440d-83a8-0fc49e1ed304	726	machine_b8caba97_4	\N	1.0.0	2026-03-16 01:12:23.94118	2026-03-16 01:12:23.941181	t
bb6cc7d0-9b32-4796-9cbb-d6dea7ed4088	728	login_machine_0898fd8e	10.0.0.1	1.0.0	2026-03-16 01:12:24.101847	2026-03-16 01:12:24.101848	t
2506007a-2984-435c-85aa-beac39e308c5	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 01:31:42.809712	2026-03-16 01:31:42.809714	t
94241877-9bfa-4a22-84ed-4a3dee56fd6e	753	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:31:47.850205	2026-03-16 01:31:47.850208	t
337d45bd-6374-42cd-bf7e-3fb67e9bc959	760	machine_2592fc81_2	\N	1.0.0	2026-03-16 01:31:49.75694	2026-03-16 01:31:49.756941	t
7f60f8ba-ae61-4319-b83d-e97eaaa77acf	754	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:31:48.216415	2026-03-16 01:31:48.286735	f
db8836e5-100c-45be-8979-1bf6c4af5f0a	755	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 01:31:48.952236	2026-03-16 01:31:48.952238	t
1a35c0c5-3eb4-4a4f-9219-439ae4f02a52	755	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:31:48.952334	2026-03-16 01:31:48.952335	t
92e1309e-68fa-4712-9603-3fd38296d9da	755	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:31:48.952385	2026-03-16 01:31:48.952386	f
d4864c90-9af9-4543-9beb-c3f293670b29	759	test_machine_e590ee4e	192.168.1.100	2512010029	2026-03-16 01:31:49.667527	2026-03-16 01:31:49.667529	t
4b8eeeae-a60c-45c3-a771-51edfe9a6394	761	machine_e9b4d5aa	\N	1.0.0	2026-03-16 01:31:49.854648	2026-03-16 01:31:49.88357	f
772cd3b0-c995-4b61-aa54-80567178d6a6	762	machine_ea4da9d1	\N	1.0.0	2026-03-16 01:31:49.973379	2026-03-16 01:31:50.100079	t
649ea9ba-42d6-465c-91e3-e7dde0e59b4d	763	machine_6f67d717_0	\N	1.0.0	2026-03-16 01:31:50.193956	2026-03-16 01:31:50.193959	t
ba6a347c-4807-4c94-a528-5d924a7a7f9b	763	machine_6f67d717_1	\N	1.0.0	2026-03-16 01:31:50.193968	2026-03-16 01:31:50.193969	f
88f32149-de8c-4f04-bff7-fbff6d2bf396	763	machine_6f67d717_2	\N	1.0.0	2026-03-16 01:31:50.193976	2026-03-16 01:31:50.193977	t
b7674c1c-5555-4631-b387-940d5f1ad0a7	763	machine_6f67d717_3	\N	1.0.0	2026-03-16 01:31:50.193984	2026-03-16 01:31:50.193984	f
25b4d780-ceb9-4a9d-95e4-4e2aa0071e7d	763	machine_6f67d717_4	\N	1.0.0	2026-03-16 01:31:50.193991	2026-03-16 01:31:50.193991	t
79669c6b-282a-4bd1-98b5-13f596b7e1bd	765	login_machine_81a3bae4	10.0.0.1	1.0.0	2026-03-16 01:31:50.381854	2026-03-16 01:31:50.381856	t
75812726-4940-4df8-b4fc-c265e13ee184	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 01:50:52.499407	2026-03-16 01:50:52.49941	t
a22dcc15-cf00-4362-a872-174613710a19	790	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:50:57.648804	2026-03-16 01:50:57.648806	t
e0c81cab-ba2d-4706-b0f5-ec8fdb878804	792	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 01:50:58.570249	2026-03-16 01:50:58.570251	t
64fa2397-ca85-4679-ba33-91f65900fa78	791	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:50:58.060737	2026-03-16 01:50:58.193007	f
82cfe2b1-0daf-489d-ad3c-35069ef93652	792	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:50:58.570358	2026-03-16 01:50:58.570359	t
fe139331-301c-4ef3-b59f-2b1e0c53ca79	792	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:50:58.57041	2026-03-16 01:50:58.57041	f
f5d0da30-2d1f-4919-bb8c-3e86c213c457	796	test_machine_f43696db	192.168.1.100	2512010029	2026-03-16 01:50:59.479122	2026-03-16 01:50:59.479125	t
8152cf5f-c388-4b60-991b-8d2f4cb2daf4	797	machine_91d8ac29_0	\N	1.0.0	2026-03-16 01:50:59.628596	2026-03-16 01:50:59.628599	t
4e274801-ded5-41ec-a010-550857e6a927	797	machine_91d8ac29_1	\N	1.0.0	2026-03-16 01:50:59.628609	2026-03-16 01:50:59.628609	t
d7ef1e67-2d4c-49c8-8a49-a2313b193a0f	797	machine_91d8ac29_2	\N	1.0.0	2026-03-16 01:50:59.628616	2026-03-16 01:50:59.628617	t
1460a112-3edb-4e72-b054-a020d8f73800	798	machine_4eb33404	\N	1.0.0	2026-03-16 01:50:59.777689	2026-03-16 01:50:59.857124	f
d1e434be-9eb2-4ce8-8192-bff0533c387b	799	machine_327ea0b0	\N	1.0.0	2026-03-16 01:51:00.009123	2026-03-16 01:51:00.179061	t
50c917aa-63ca-4529-b53f-512d2ef79436	800	machine_890dee91_0	\N	1.0.0	2026-03-16 01:51:00.330143	2026-03-16 01:51:00.330146	t
d4b56d43-cddd-46ed-b2c8-9b839bcab929	800	machine_890dee91_1	\N	1.0.0	2026-03-16 01:51:00.330155	2026-03-16 01:51:00.330156	f
bfa2853a-c86d-420a-a90a-368480c8adde	800	machine_890dee91_2	\N	1.0.0	2026-03-16 01:51:00.330163	2026-03-16 01:51:00.330164	t
4a62585c-dfdd-402c-a734-6d7dcc484da1	800	machine_890dee91_3	\N	1.0.0	2026-03-16 01:51:00.33017	2026-03-16 01:51:00.330171	f
6721987f-ff98-4f70-b7e0-d29889fb5a12	800	machine_890dee91_4	\N	1.0.0	2026-03-16 01:51:00.330177	2026-03-16 01:51:00.330178	t
8d8dcdd9-e3cc-4722-898c-c34e7d659aa7	802	login_machine_4f5fc381	10.0.0.1	1.0.0	2026-03-16 01:51:00.65165	2026-03-16 01:51:00.651652	t
ad4287e7-c86d-4300-a002-6c5b41d4d8a0	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 01:57:17.49577	2026-03-16 01:57:17.495772	t
5540cce4-1594-4d38-9db3-d05fa5bde99b	827	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:57:23.167398	2026-03-16 01:57:23.167401	t
7c54ea48-b441-464c-b070-09b56f11b2cf	876	login_machine_e3798862	10.0.0.1	1.0.0	2026-03-16 02:37:39.486888	2026-03-16 02:37:39.486889	t
341f0b3a-3bf3-4b67-8910-ec28287352e8	828	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:57:23.600439	2026-03-16 01:57:23.723102	f
774f470f-2c94-4dbe-8c13-ce4ff1f325ac	829	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 01:57:24.145598	2026-03-16 01:57:24.1456	t
adcf44aa-0854-43d6-a7b9-16a9541c5d8e	829	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 01:57:24.145668	2026-03-16 01:57:24.145668	t
d0aed160-2bba-4e5c-8a07-eae56e4de7af	829	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 01:57:24.145699	2026-03-16 01:57:24.145699	f
8420d517-f2d9-43f6-b842-059633cf90cc	833	test_machine_405fdcd5	192.168.1.100	2512010029	2026-03-16 01:57:25.130342	2026-03-16 01:57:25.130344	t
4906a9df-bc44-47d6-9d46-7ca7f1d82627	834	machine_228fc041_0	\N	1.0.0	2026-03-16 01:57:25.270984	2026-03-16 01:57:25.270987	t
aa5b4263-d7d1-480d-83f2-185987645c30	834	machine_228fc041_1	\N	1.0.0	2026-03-16 01:57:25.270993	2026-03-16 01:57:25.270993	t
053baaad-e92a-48a2-bc42-3a96d5e4e8e5	834	machine_228fc041_2	\N	1.0.0	2026-03-16 01:57:25.270998	2026-03-16 01:57:25.270998	t
983c2b16-d776-4e2f-b5f3-8d8d69a8b1be	835	machine_f7b46f0f	\N	1.0.0	2026-03-16 01:57:25.467156	2026-03-16 01:57:25.52205	f
8639ac6f-570f-4eca-899c-e4779801faf2	836	machine_945a08d8	\N	1.0.0	2026-03-16 01:57:25.743731	2026-03-16 01:57:25.964375	t
c61881e6-892b-4690-b4a6-f95b37500252	837	machine_6d1512a1_0	\N	1.0.0	2026-03-16 01:57:26.144939	2026-03-16 01:57:26.14494	t
739590db-8bac-4bce-ae7f-8f1a4efb158a	837	machine_6d1512a1_1	\N	1.0.0	2026-03-16 01:57:26.144946	2026-03-16 01:57:26.144946	f
2e66b339-2ac5-4182-92d5-514929d7e5cc	837	machine_6d1512a1_2	\N	1.0.0	2026-03-16 01:57:26.14495	2026-03-16 01:57:26.144951	t
3e7041d1-c3b7-4bef-b3c4-332d502e9e12	837	machine_6d1512a1_3	\N	1.0.0	2026-03-16 01:57:26.144954	2026-03-16 01:57:26.144954	f
f8f1070f-b7ba-435b-a7ec-22807056b6a7	837	machine_6d1512a1_4	\N	1.0.0	2026-03-16 01:57:26.144957	2026-03-16 01:57:26.144957	t
7b6cafbe-8dab-45d6-a01a-0091264149bb	839	login_machine_26229cb1	10.0.0.1	1.0.0	2026-03-16 01:57:26.567772	2026-03-16 01:57:26.567773	t
096774f2-be30-4a34-9e47-11b325ed0911	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 02:37:26.391272	2026-03-16 02:37:26.391274	t
88e7b7c9-9ad3-4be4-97b2-59d04783f302	864	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 02:37:32.675435	2026-03-16 02:37:32.675436	t
400c9b09-5898-4917-95ec-e733931bc941	13	test-machine-001	127.0.0.1	1.0.0	2026-03-16 02:40:40.66619	2026-03-16 02:40:40.666192	t
28acf809-8c5f-4d62-a4af-84ce82d36bc2	865	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 02:37:33.422593	2026-03-16 02:37:33.806555	f
81c90bd1-247a-4e44-b7df-f2bda1c22357	866	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 02:37:34.389239	2026-03-16 02:37:34.389241	t
dc36ac9a-c161-4a5e-be47-5f8632afaff9	866	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 02:37:34.38932	2026-03-16 02:37:34.38932	t
d6821451-dd67-4920-acee-499bdea0f551	866	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 02:37:34.389351	2026-03-16 02:37:34.389351	f
2e19ab06-a15f-47e0-97fb-3334a1920588	870	test_machine_5d05cf15	192.168.1.100	2512010029	2026-03-16 02:37:36.224671	2026-03-16 02:37:36.224673	t
6014496b-34a6-4274-9b9f-70fd5e58d9b7	871	machine_95916779_0	\N	1.0.0	2026-03-16 02:37:36.664664	2026-03-16 02:37:36.664667	t
54c7a95c-4a93-4146-af25-f3e4c3cc9fc5	871	machine_95916779_1	\N	1.0.0	2026-03-16 02:37:36.664673	2026-03-16 02:37:36.664673	t
2855912f-5cb5-430b-8ddb-a981de33b157	871	machine_95916779_2	\N	1.0.0	2026-03-16 02:37:36.664677	2026-03-16 02:37:36.664677	t
8f5cbbdf-4675-42e9-9d29-1a20234327ff	872	machine_1188635b	\N	1.0.0	2026-03-16 02:37:37.056374	2026-03-16 02:37:37.24321	f
7735ef52-18a0-478a-836c-fca8d472a53d	873	machine_546c0fff	\N	1.0.0	2026-03-16 02:37:37.609125	2026-03-16 02:37:37.898874	t
9b3841a1-8329-4499-ac24-9c7b33d82e68	874	machine_c32d81ed_0	\N	1.0.0	2026-03-16 02:37:38.428696	2026-03-16 02:37:38.428699	t
4dba2ed6-b08d-41e7-ad2b-bfd6ab717fc2	874	machine_c32d81ed_1	\N	1.0.0	2026-03-16 02:37:38.428704	2026-03-16 02:37:38.428704	f
b6018185-824f-4f27-bc6d-da54e58d997c	874	machine_c32d81ed_2	\N	1.0.0	2026-03-16 02:37:38.428708	2026-03-16 02:37:38.428708	t
3b091e93-adb9-4c5e-a4f9-d5ead88df0b4	874	machine_c32d81ed_3	\N	1.0.0	2026-03-16 02:37:38.428712	2026-03-16 02:37:38.428712	f
b8037733-9a28-4486-a029-588de5dc4eb2	874	machine_c32d81ed_4	\N	1.0.0	2026-03-16 02:37:38.428715	2026-03-16 02:37:38.428715	t
8b39a4ad-53e5-4574-aac3-ed4239e5ff54	901	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 02:40:45.713037	2026-03-16 02:40:45.71304	t
397446a3-f00b-4246-80b2-e0d4ad8f5cdb	907	test_machine_e1c8b268	192.168.1.100	2512010029	2026-03-16 02:40:47.682889	2026-03-16 02:40:47.682892	t
25e6aef3-64cf-4e58-93f4-6725a813d2f9	902	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 02:40:46.119501	2026-03-16 02:40:46.290569	f
9a8a6313-2df7-44d9-ad19-fbe79eb286f5	903	test-machine-000	127.0.0.1	1.0.0-test	2026-03-16 02:40:46.721785	2026-03-16 02:40:46.721787	t
10b56b47-dec6-442b-9021-31b623c97297	903	test-machine-001	127.0.0.1	1.0.0-test	2026-03-16 02:40:46.72186	2026-03-16 02:40:46.721861	t
a2fa1d3c-3b2f-4080-a371-b5dd7951e658	903	test-machine-002	127.0.0.1	1.0.0-test	2026-03-16 02:40:46.721891	2026-03-16 02:40:46.721891	f
ea653ae9-9d7c-4caa-aa05-911099299a70	908	machine_c64d3c1c_0	\N	1.0.0	2026-03-16 02:40:47.815314	2026-03-16 02:40:47.815317	t
27a3ab56-c7b3-4567-a3f8-aa87cd5e7b01	908	machine_c64d3c1c_1	\N	1.0.0	2026-03-16 02:40:47.815322	2026-03-16 02:40:47.815322	t
8a7232af-292e-4f25-a2f9-985d2ce215b8	908	machine_c64d3c1c_2	\N	1.0.0	2026-03-16 02:40:47.815326	2026-03-16 02:40:47.815326	t
62bec7e0-31a4-4823-bb50-356c754c1850	909	machine_ab1ce8e8	\N	1.0.0	2026-03-16 02:40:47.959437	2026-03-16 02:40:48.012741	f
18d10724-1663-4909-b02b-06161fd117ad	910	machine_034e7353	\N	1.0.0	2026-03-16 02:40:48.183472	2026-03-16 02:40:48.365872	t
2d2500e5-1988-4b3c-a89e-fc90d11feeb9	911	machine_9daef38f_0	\N	1.0.0	2026-03-16 02:40:48.507171	2026-03-16 02:40:48.507173	t
630388cd-8b88-4567-b92d-b2c303515708	911	machine_9daef38f_1	\N	1.0.0	2026-03-16 02:40:48.507178	2026-03-16 02:40:48.507179	f
c596db55-9b9a-48cb-a2de-fd7d81785c0f	911	machine_9daef38f_2	\N	1.0.0	2026-03-16 02:40:48.507182	2026-03-16 02:40:48.507182	t
fa137434-a973-4041-964e-60313cb005f4	911	machine_9daef38f_3	\N	1.0.0	2026-03-16 02:40:48.507185	2026-03-16 02:40:48.507186	f
b861fdf6-0d2e-463f-b5ed-b8dd7cb7f06f	911	machine_9daef38f_4	\N	1.0.0	2026-03-16 02:40:48.507189	2026-03-16 02:40:48.507189	t
625a821e-402a-40dd-9cb0-eb34ab667a77	913	login_machine_1bb4ef9c	10.0.0.1	1.0.0	2026-03-16 02:40:48.813429	2026-03-16 02:40:48.81343	t
\.


--
-- Data for Name: telemetry_summary; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.telemetry_summary (summary_id, date, installation_id, total_sessions, total_duration_seconds, avg_session_seconds, tools_used, total_operations, info_count, success_count, warning_count, error_count, critical_count, updated_at) FROM stdin;
1	2026-01-31 00:00:00	mn2fWJtp3-SwBjxNnaTnGA	1	2	2	null	0	2	0	1	1	0	2026-01-31 06:28:52.007682
2	2026-01-31 00:00:00	WumatQvn4rsS7-t3sWNsNw	1	0	0	null	0	3	0	0	0	0	2026-01-31 06:28:54.060121
\.


--
-- Data for Name: tool_usage_stats; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.tool_usage_stats (stat_id, date, tool_name, total_uses, unique_users, total_duration_seconds, avg_duration_seconds, success_count, error_count) FROM stdin;
\.


--
-- Data for Name: update_history; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.update_history (update_id, user_id, from_version, to_version, update_timestamp, machine_id) FROM stdin;
\.


--
-- Data for Name: user_activity_summary; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.user_activity_summary (summary_id, date, user_id, username, total_operations, total_duration_seconds, tools_used, first_activity, last_activity) FROM stdin;
\.


--
-- Data for Name: user_capabilities; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.user_capabilities (id, user_id, capability_name, granted_by, granted_at, expires_at) FROM stdin;
\.


--
-- Data for Name: user_feedback; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.user_feedback (feedback_id, user_id, "timestamp", feedback_type, tool_name, subject, description, rating, status, admin_response) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: localization_admin
--

COPY public.users (user_id, username, password_hash, email, full_name, department, team, language, role, is_active, created_at, created_by, last_login, last_password_change, must_change_password) FROM stdin;
11	test_duplicate	$2b$12$nyw2V5JjvEePu3zsYOy6IOEj4ijSxI3ymHUpIL2a.3w6vmnwtCAhC	\N	\N	\N	\N	\N	user	t	2025-12-16 05:44:48.630423	2	\N	\N	f
25	log_test_1765831510	$2b$12$/889UfgDzpYrx54qoEU2K.jqKPsj9kmoipH3sNlTlJNix1zhVy2C2	log_test_1765831510@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-16 05:45:10.931743	\N	\N	\N	f
26	session_test_1765831511	$2b$12$wagGQlPaizIDBIPvK1lWOePcJ.iq4D/EDJHvZPpAf5MMzFnHTS11G	session_test_1765831511@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-16 05:45:11.200742	\N	\N	\N	f
27	session_update_1765831511	$2b$12$E7X8oDGreRzOsLu.YOQYPOn90dJXKZR6eco7B8k.IZEkeO2rix2DO	session_update_1765831511@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-16 05:45:11.511129	\N	\N	\N	f
28	session_filter_1765831511	$2b$12$Ea2.622yJXJiz9g0ZN4CuOPlAy68BQqr34Gy0WI63P/Sqh.UntVWm	session_filter_1765831511@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-16 05:45:11.831739	\N	\N	\N	f
29	hashtest_47d2112a	$2b$12$RzFtTbpaNOKwhpOAAgozBe3aip1Bb2Uh5I4RejEhCBsyO8VgU4Ltu	hash_47d2112a@test.com	\N	\N	\N	\N	user	t	2025-12-16 05:45:12.108781	\N	\N	\N	f
3	test_profile_863871	$2b$12$gUGxwmkbAFm62G08MwGw4OjOAftHt2C926em4mSunQy9PyDKfh9N.	\N	Test User	\N	Team Alpha	Japanese	user	f	2025-12-16 05:44:41.102878	2	\N	\N	f
13	testuser	$2b$12$CClOVR2CfYeyV8tag1LWK.poK/YXN4Ni4PzynLLMEt7BT1F/2uwaK	test@example.com	Test User	Testing	\N	\N	user	t	2025-12-16 05:45:05.803494	\N	2026-03-16 02:40:40.975313	\N	f
4	test_created_863871	$2b$12$7eajFP5Z.m7tmDXq1MKTyulKK5Ta5frH1jr2It7Z42I45RDDnWOjS	\N	\N	\N	\N	\N	user	f	2025-12-16 05:44:41.60316	2	\N	\N	f
51	logtest_user	hash	\N	\N	QA	\N	\N	user	t	2025-12-16 05:45:14.876759	\N	\N	\N	f
30	admin_test_f72a1e05	admin_hash	admin_f72a1e05@test.com	\N	\N	\N	\N	admin	t	2025-12-16 05:45:12.344616	\N	\N	\N	f
12	regular_user	$2b$12$PmyW/OF2fn3oxt3jLET1tupKZ9M9nS7oaCse76zqt/0mW7GAeh.8y	\N	\N	\N	\N	\N	user	t	2025-12-16 05:44:49.5215	2	2026-03-16 03:21:23.220075	\N	f
31	deactivate_dc792b46	hash	\N	\N	\N	\N	\N	user	f	2025-12-16 05:45:12.429174	\N	\N	\N	f
32	sessiontest_aa0f8f77	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:12.532456	\N	\N	\N	f
33	multisession_1e2f794c	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:12.599731	\N	\N	\N	f
14	auth_user_1765831507	$2b$12$rT/cCUzuf8i0oFX9Qv4u2e7WxFmPhU3yUF3VwRHM8XtuIIllqTHkm	auth_user_1765831507@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-16 05:45:07.998031	\N	\N	\N	f
7	test_fullprof_863871	$2b$12$SzvJkCES41Fvhl20iHn/UeqRf5TOVOodrrbfV6JrYCcKvnoX4263C	test_863871@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2025-12-16 05:44:45.506647	2	\N	\N	f
15	regular_user_1765831508	$2b$12$8WDTtu6TAxvtx3J7NXwo/OvR7q1x5IM.kf..FFZdGaOrR61Ln/nVG	regular_1765831508@example.com	Regular User	Testing	\N	\N	user	t	2025-12-16 05:45:08.592668	\N	\N	\N	f
8	test_update_profile	$2b$12$Kqx.4Lk3jFmtu0vlgel0u.JmnMOSihRSBcitaESNDvl1yd8893oeW	\N	Updated Name	\N	Team B	Korean	user	t	2025-12-16 05:44:46.074245	2	\N	\N	f
16	admin_user_1765831508	$2b$12$DHI.7Lx1CR3K7oN5ujmPjeosk1cwqG4sxwxjzT/4FCsYQta3l/JHq	admin_1765831508@example.com	Admin User	IT	\N	\N	admin	t	2025-12-16 05:45:08.776252	\N	\N	\N	f
34	endsession_f858a480	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:12.669056	\N	\N	\N	f
17	activation_test_1765831508	$2b$12$Q9YDhuRCTFJjk5le2HaQdOSCbrEArbc1Lm7lzO71tSsXffBWXgGY.	activation_1765831508@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-16 05:45:09.019282	\N	\N	\N	f
18	dept_user_1765831509_0	$2b$12$Xp0LYtaCTrA0IsaEbQpR..AEKr/mLCJmf2JaGS4PzAYHxtTUf8KG.	dept_user_1765831509_0@example.com	Dept User 0	TestDept_1765831509	\N	\N	user	t	2025-12-16 05:45:09.306416	\N	\N	\N	f
35	activity_468be304	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:12.754231	\N	\N	\N	f
19	dept_user_1765831509_1	$2b$12$7BplBBM6t.EqgcZZsPUp9utL2lIHDnN3B0gMMnC2ZWE1eBYH2bXOW	dept_user_1765831509_1@example.com	Dept User 1	TestDept_1765831509	\N	\N	user	t	2025-12-16 05:45:09.49283	\N	\N	\N	f
20	dept_user_1765831509_2	$2b$12$xTCtxIu1BjDg3DY1EROLwOPvQcIcHeNql0RmU9OhJ7IBIjFKP1R.u	dept_user_1765831509_2@example.com	Dept User 2	TestDept_1765831509	\N	\N	user	t	2025-12-16 05:45:09.675735	\N	\N	\N	f
21	unique_test_1765831509	$2b$12$JkasS/7mIms.yqv3VRIH0.8CRUA.HXlEsK1PaZ/AsEV6LTUvU.HF.	unique_1765831509@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-16 05:45:09.934584	\N	\N	\N	f
22	login_test_1765831509	$2b$12$wpje3eIaKRFvMZ9DrQ2jWu5HIJoh2PRnUkFags0uiOr6muj2.z65K	login_test_1765831509@example.com	Login Test	Testing	\N	\N	user	t	2025-12-16 05:45:10.168947	\N	2025-12-16 05:45:10.209237	\N	f
23	test_async_1765831510	$2b$12$rfNgWRdR8YqhQpl9fA2X5.5WGRPo5rSETQVKLAg7xcxMLqfd.R2Ei	test_async_1765831510@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-16 05:45:10.445157	\N	\N	\N	f
24	auth_test_1765831510	$2b$12$QRHHgnunp4Oy51HXbAtoIu7wwiGnYDkrRgl9qAdPsAV/tcsmzUb8W	auth_test_1765831510@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-16 05:45:10.7002	\N	\N	\N	f
36	findactive_be40e1e6	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:12.945133	\N	\N	\N	f
37	loginuser_97cafbb7	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:13.012043	\N	2025-12-16 05:45:13.033531	\N	f
38	createsession_1ba45a66	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:13.078022	\N	2025-12-16 05:45:13.100272	\N	f
39	plaintext_test_3a77abf6	$2b$12$n/HTmdqQJvN1H6Wpx4P.O.NQ.zf9jW4f7TYl4gOgfV1rrqbTyYa3.	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:13.338083	\N	\N	\N	f
40	user1_2bebd86d	$2b$12$jWCWnJwyKtSX/Op6dIgJ8.SmC/HN28oN9EAmMn/Ih42Hg9hBZPf1C	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:13.780336	\N	\N	\N	f
41	user2_2bebd86d	$2b$12$WJ7bADMYuP.6.w97AhA8kOeXjmS9RIFi9p3YVgaRzUhJVtee45Izi	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:13.780339	\N	\N	\N	f
42	user_user_5c766680	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:14.196834	\N	\N	\N	f
43	admin_user_5c766680	hash	\N	\N	\N	\N	\N	admin	t	2025-12-16 05:45:14.196836	\N	\N	\N	f
44	superadmin_user_5c766680	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-16 05:45:14.196837	\N	\N	\N	f
45	norole_b56147ef	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:14.253645	\N	\N	\N	f
46	mixed_9903be34_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-16 05:45:14.326749	\N	\N	\N	f
47	mixed_9903be34_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-16 05:45:14.326752	\N	\N	\N	f
48	mixed_9903be34_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:14.326752	\N	\N	\N	f
49	mixed_9903be34_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:14.326753	\N	\N	\N	f
50	mixed_9903be34_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:45:14.326753	\N	\N	\N	f
52	hashtest_0a9151b1	$2b$12$bW6TkyPxnw5Mouk2qEkGTeFum3WGd0trTOs5FD/5qMgNV/kZ07sXS	hash_0a9151b1@test.com	\N	\N	\N	\N	user	t	2025-12-16 05:46:56.839529	\N	\N	\N	f
53	admin_test_3dd3dfdb	admin_hash	admin_3dd3dfdb@test.com	\N	\N	\N	\N	admin	t	2025-12-16 05:46:57.076877	\N	\N	\N	f
54	deactivate_21dd3915	hash	\N	\N	\N	\N	\N	user	f	2025-12-16 05:46:57.124734	\N	\N	\N	f
55	sessiontest_1d7ed5b8	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:57.233283	\N	\N	\N	f
56	multisession_8bbda1de	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:57.301235	\N	\N	\N	f
57	endsession_780fb52e	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:57.371309	\N	\N	\N	f
58	activity_9652c073	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:57.469582	\N	\N	\N	f
59	findactive_6493649b	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:57.771868	\N	\N	\N	f
60	loginuser_971abd13	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:57.844317	\N	2025-12-16 05:46:57.869539	\N	f
61	createsession_a9d12fe4	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:57.914754	\N	2025-12-16 05:46:57.936498	\N	f
62	plaintext_test_ad508e63	$2b$12$V/ckxP0iGgijW8gSzz4YeOcgcd44PXSHWjwXEJLlmDw/Ey696P/i.	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:58.162369	\N	\N	\N	f
63	user1_5e7b95b6	$2b$12$dKK8FkvDg/XHl3sy.6gvj.7M5DtuKQxScZB.GhhG6if5tMlC2aRta	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:58.563368	\N	\N	\N	f
64	user2_5e7b95b6	$2b$12$Krfq.UaYyEqBUbnDC.OKhuf36NIembCb1Mwb2WqFz372jHF3Chaz.	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:58.563371	\N	\N	\N	f
65	user_user_71e9988f	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:58.968856	\N	\N	\N	f
66	admin_user_71e9988f	hash	\N	\N	\N	\N	\N	admin	t	2025-12-16 05:46:58.968858	\N	\N	\N	f
67	superadmin_user_71e9988f	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-16 05:46:58.968858	\N	\N	\N	f
68	norole_cb7e346f	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:59.020271	\N	\N	\N	f
69	mixed_f2846203_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-16 05:46:59.062824	\N	\N	\N	f
70	mixed_f2846203_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-16 05:46:59.062826	\N	\N	\N	f
71	mixed_f2846203_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:59.062827	\N	\N	\N	f
72	mixed_f2846203_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:59.062827	\N	\N	\N	f
73	mixed_f2846203_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-16 05:46:59.062827	\N	\N	\N	f
74	auth_user_1765831619	$2b$12$abTB2RZEtsdYm99SNqRw3uA/4A5aEcAgxdkFRI3dGDeii2oDnT2tO	auth_user_1765831619@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-16 05:46:59.265813	\N	\N	\N	f
75	regular_user_1765831619	$2b$12$sqiOyku3/evJ4MoIbFiik.GzItlE2lglpHBa.cd5UtTtrvhEWllDq	regular_1765831619@example.com	Regular User	Testing	\N	\N	user	t	2025-12-16 05:46:59.853331	\N	\N	\N	f
76	admin_user_1765831619	$2b$12$IJ9qo2jvfvgDbB7nQpciQey7n1RUzu567Ic5Ix0WN9w2bA9odnnCq	admin_1765831619@example.com	Admin User	IT	\N	\N	admin	t	2025-12-16 05:47:00.030881	\N	\N	\N	f
90	unique_test_1766292074	$2b$12$i2gDEoapfPB2yq8U24JxEeQ9mtVt91dm50qLcU9r7m.qktB3nV3XO	unique_1766292074@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-21 13:41:15.09064	\N	\N	\N	f
77	activation_test_1765831620	$2b$12$i3SN6o04yYxjvnu1fe353eUrPz2M2meutXApjyfrIHh5S821F2pky	activation_1765831620@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-16 05:47:00.264755	\N	\N	\N	f
78	dept_user_1765831620_0	$2b$12$vegYvm.CI8R8JEda0OK0E.5.smyWZHWN3crcgRowGjGhnqhA2X8s.	dept_user_1765831620_0@example.com	Dept User 0	TestDept_1765831620	\N	\N	user	t	2025-12-16 05:47:00.704995	\N	\N	\N	f
79	dept_user_1765831620_1	$2b$12$AZ7dILioKn2pK7tEjsEelOXKcMIr9BOld5.vwYEAAlsKPnV8Zr2zi	dept_user_1765831620_1@example.com	Dept User 1	TestDept_1765831620	\N	\N	user	t	2025-12-16 05:47:00.885187	\N	\N	\N	f
80	dept_user_1765831620_2	$2b$12$iQf6sKrURw8minxx.rl9ue0piQzFYzO5q8ONoyeuU./hxubjnrbM.	dept_user_1765831620_2@example.com	Dept User 2	TestDept_1765831620	\N	\N	user	t	2025-12-16 05:47:01.062666	\N	\N	\N	f
81	unique_test_1765831621	$2b$12$xbHzx5oFXw6KGkI7/f7hc.EOc6PNd/UzPX0vkrAnvhajZnaXZ2Mly	unique_1765831621@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-16 05:47:01.27359	\N	\N	\N	f
82	login_test_1765831621	$2b$12$E1p3ZqxqXa28lb0pXmvI7.SHBYqMe/NFxjj.lMV.QuVEhhkbQIJnS	login_test_1765831621@example.com	Login Test	Testing	\N	\N	user	t	2025-12-16 05:47:01.502587	\N	2025-12-16 05:47:01.565885	\N	f
91	login_test_1766292075	$2b$12$NKJmK86Z7u0sG3Wm9WPV/uIrdjKAVSK329wuP1nqsSYfznWEp2WtK	login_test_1766292075@example.com	Login Test	Testing	\N	\N	user	t	2025-12-21 13:41:15.465826	\N	2025-12-21 13:41:15.567605	\N	f
92	test_async_1766292075	$2b$12$4eKN2eWimHAjutZoe8EmTuxXz6WeRR.AjFIY6N0DiZu517LMU1yWa	test_async_1766292075@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-21 13:41:15.884162	\N	\N	\N	f
93	auth_test_1766292075	$2b$12$dJrTKDBtbUfoUQUT1XrU0ufX8b5B3pJYD7vpDhrUEdNF0ZFH1fRIW	auth_test_1766292075@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-21 13:41:16.197392	\N	\N	\N	f
94	log_test_1766292076	$2b$12$qikA4zKbnOxDbkQmX8a1X.5lHozeZTcTxLaoGe2dhHDrnMUW2p1By	log_test_1766292076@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-21 13:41:16.524712	\N	\N	\N	f
95	session_test_1766292076	$2b$12$kQrmRqRkBfkBQ1VXhRG7Du7L9jRkUlIzK46Dx4ac1IZqt0Pqhr0dG	session_test_1766292076@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-21 13:41:16.940356	\N	\N	\N	f
96	session_update_1766292084	$2b$12$AwTU2AMtkw8J2YWhlw1md.ZutBhl78hHR5OeTPt9tyvbhCxgYwo1e	session_update_1766292084@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-21 13:41:16.838631	\N	\N	\N	f
83	auth_user_1766292072	$2b$12$H2.UdkCoBgpQLK2OvH7ww.U9r9W/2hk83fkKrLM/bRRDeUF3xshqK	auth_user_1766292072@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-21 13:41:12.294509	\N	\N	\N	f
84	regular_user_1766292072	$2b$12$zEFjsFDEj45J6w/DxHV8A.4u/WF32bufWZJKgZapGYTAwER4Pcqv.	regular_1766292072@example.com	Regular User	Testing	\N	\N	user	t	2025-12-21 13:41:13.177171	\N	\N	\N	f
85	admin_user_1766292072	$2b$12$I1rrOWCX/m/x8J3dyPAgT.hIWowA6ZecWQvuyJtU.wKkN8Q2YEK2W	admin_1766292072@example.com	Admin User	IT	\N	\N	admin	t	2025-12-21 13:41:13.394715	\N	\N	\N	f
97	session_filter_1766292077	$2b$12$Fm1HSxlFLrBhYKLI72vBjeYPxPbKkyI7U6J6wJH2soYr4/ETFjcRy	session_filter_1766292077@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-21 13:41:17.359484	\N	\N	\N	f
86	activation_test_1766292073	$2b$12$ERQP3/jE5L7nfyKK2uJtS.780gwnKdFKV4rSVLflKI1IVDoX9wAYa	activation_1766292073@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-21 13:41:13.732741	\N	\N	\N	f
87	dept_user_1766292073_0	$2b$12$TxLLebvf6fIGIxXCgpID9e74wKw6ttJ4d.1LbZZokk5CA8CMisSXC	dept_user_1766292073_0@example.com	Dept User 0	TestDept_1766292073	\N	\N	user	t	2025-12-21 13:41:14.157178	\N	\N	\N	f
98	hashtest_a0a91df7	$2b$12$4SmSwXGv8LdoGoqiwfqFne1L2v9VzfN5HEeNCEUPz1sLoVOpYTjAC	hash_a0a91df7@test.com	\N	\N	\N	\N	user	t	2025-12-21 13:41:17.784669	\N	\N	\N	f
88	dept_user_1766292073_1	$2b$12$cY6Ky5lAsPjvP8tv/j9u4uC5jQh5wmojtVy0pssFgyFtS69wIC.4e	dept_user_1766292073_1@example.com	Dept User 1	TestDept_1766292073	\N	\N	user	t	2025-12-21 13:41:14.373593	\N	\N	\N	f
89	dept_user_1766292073_2	$2b$12$.1ggd5QjcrL8e2K3FfGYJORV/jMIXF5qf9L8OC/8la3zUazIT6GNS	dept_user_1766292073_2@example.com	Dept User 2	TestDept_1766292073	\N	\N	user	t	2025-12-21 13:41:14.591114	\N	\N	\N	f
99	admin_test_dc1d0d1b	admin_hash	admin_dc1d0d1b@test.com	\N	\N	\N	\N	admin	t	2025-12-21 13:41:18.091642	\N	\N	\N	f
100	deactivate_991e39bf	hash	\N	\N	\N	\N	\N	user	f	2025-12-21 13:41:18.166968	\N	\N	\N	f
101	sessiontest_70c5b254	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:18.332493	\N	\N	\N	f
102	multisession_46ffb24b	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:18.513112	\N	\N	\N	f
103	endsession_762f4549	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:18.615169	\N	\N	\N	f
104	activity_3b8aaafa	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:18.752279	\N	\N	\N	f
105	findactive_71f1d056	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:18.990011	\N	\N	\N	f
106	loginuser_f8aa9ea3	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:19.18158	\N	2025-12-21 13:41:19.275301	\N	f
107	createsession_8f7b6553	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:19.357527	\N	2025-12-21 13:41:19.392432	\N	f
108	plaintext_test_81114b8d	$2b$12$i.HCpZbVRM.lyUA8uKBV1evE4wU6ZBn7r8tD3BdzpCfuPGwa.HAP.	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:19.692	\N	\N	\N	f
109	user1_b076b4a2	$2b$12$BOaFMY.ch8GPBweIdA.vnOQZx2ramUNsCdV3KYyKARJNRTliKEGse	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:20.21149	\N	\N	\N	f
110	user2_b076b4a2	$2b$12$m/MAye/yAdx0jhS3XwTjpeMVabgXMhzdiFYg2w5sJOPYGVfqJIxoe	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:20.211494	\N	\N	\N	f
111	user_user_f51c1451	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:20.813375	\N	\N	\N	f
112	admin_user_f51c1451	hash	\N	\N	\N	\N	\N	admin	t	2025-12-21 13:41:20.81338	\N	\N	\N	f
113	superadmin_user_f51c1451	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-21 13:41:20.813381	\N	\N	\N	f
114	norole_127d1ec9	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:20.900363	\N	\N	\N	f
115	mixed_e7ae44cc_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-21 13:41:20.975458	\N	\N	\N	f
116	mixed_e7ae44cc_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-21 13:41:20.975463	\N	\N	\N	f
117	mixed_e7ae44cc_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:20.975464	\N	\N	\N	f
118	mixed_e7ae44cc_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:20.975464	\N	\N	\N	f
119	mixed_e7ae44cc_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-21 13:41:20.975465	\N	\N	\N	f
120	auth_user_1766337640	$2b$12$o2uoWvrrIPnkHMt70tbb7Oa9ZWh4RD7dYg/.FxUojfOW520XSgQru	auth_user_1766337640@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 02:20:40.670342	\N	\N	\N	f
121	regular_user_1766337641	$2b$12$0cMZRi7VecIAM9NEfsH/EOCsAh2zojI.qxwjnpxv1pfUUuyYJz.ja	regular_1766337641@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 02:20:41.384349	\N	\N	\N	f
122	admin_user_1766337641	$2b$12$WuX.HHqwMW/YCh3heD2qWu5uwbynTwH/3erApGqDKFIz82PS0GLn6	admin_1766337641@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 02:20:41.589497	\N	\N	\N	f
151	norole_1a4c6fd5	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:47.955855	\N	\N	\N	f
123	activation_test_1766337641	$2b$12$IyWmAyK36eCZ8Nc1FdXucudmX5SGURZpYpzWAi/dPy1qMbELf3mrm	activation_1766337641@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 02:20:41.890837	\N	\N	\N	f
124	dept_user_1766337642_0	$2b$12$VlgNjiOhMO1VKGfXZGOiGOFWGGT6sssFb.JLTjWw0I2qrMtnEp9pu	dept_user_1766337642_0@example.com	Dept User 0	TestDept_1766337642	\N	\N	user	t	2025-12-22 02:20:42.274936	\N	\N	\N	f
125	dept_user_1766337642_1	$2b$12$.xbZjP5Udf0/N/vTcraABuRQLC.PH9DRePmSUdZlwrAIpxn.cg2.G	dept_user_1766337642_1@example.com	Dept User 1	TestDept_1766337642	\N	\N	user	t	2025-12-22 02:20:42.480076	\N	\N	\N	f
126	dept_user_1766337642_2	$2b$12$dv/yXjc3qd3Vr564kOycjezPFcTCzSPMO1nS9H0fIxULyY1EAnubi	dept_user_1766337642_2@example.com	Dept User 2	TestDept_1766337642	\N	\N	user	t	2025-12-22 02:20:42.685399	\N	\N	\N	f
127	unique_test_1766337642	$2b$12$9P78SVHTxe2gA4Od6fwj8.zTolHgTdgCTY1L/Yquz/Z8ZWqbrTLki	unique_1766337642@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 02:20:42.940785	\N	\N	\N	f
128	login_test_1766337643	$2b$12$NAdLYHFr98pL.8.4z0wVvOSLI5nBnCkmntVo.zPHB0qX/vd5mKav2	login_test_1766337643@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 02:20:43.257888	\N	2025-12-22 02:20:43.349017	\N	f
129	test_async_1766337643	$2b$12$AIzcv4AzAubgIjtOu69AIu31O1mjg7B6beqndHHU1xUK2YdpihR1a	test_async_1766337643@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 02:20:52.233602	\N	\N	\N	f
130	auth_test_1766337652	$2b$12$UnqAUNb8be4cwF/wdcOb8ODjkHVyePQJR7J8q/imzF6kaLqqeMqJO	auth_test_1766337652@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 02:20:43.449209	\N	\N	\N	f
131	log_test_1766337643	$2b$12$.TwdtL6sA8BIDqzjRcVnM.oyElFUyJ1vsJ8PVyBEXOr864MeNz.2i	log_test_1766337643@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 02:20:43.757722	\N	\N	\N	f
132	session_test_1766337644	$2b$12$wUjDWpajUbBe/PQNdq7eXeEgvkRXEfBniwdTIHwy0VvLlFt3BPy02	session_test_1766337644@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 02:20:44.206129	\N	\N	\N	f
133	session_update_1766337644	$2b$12$bYc9bBMWbAmBjDxghWrYr.g5ibDuGVVoFbvI.Gmh1zxsEElQImmkK	session_update_1766337644@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 02:20:44.590018	\N	\N	\N	f
134	session_filter_1766337644	$2b$12$5pqX6sJDDv02G0oIulCJZ.UglwH3rKd5CDqNNwF7up8Rj.THsDimq	session_filter_1766337644@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 02:20:45.086458	\N	\N	\N	f
135	hashtest_c9cdaa25	$2b$12$3fZy5DfciRJiZknXiv8vf./I6kS4PMT.cD9drlTomlozL345tlImu	hash_c9cdaa25@test.com	\N	\N	\N	\N	user	t	2025-12-22 02:20:45.453092	\N	\N	\N	f
136	admin_test_0febdb75	admin_hash	admin_0febdb75@test.com	\N	\N	\N	\N	admin	t	2025-12-22 02:20:45.713386	\N	\N	\N	f
137	deactivate_01b223d6	hash	\N	\N	\N	\N	\N	user	f	2025-12-22 02:20:45.768856	\N	\N	\N	f
138	sessiontest_36f1176f	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:45.841095	\N	\N	\N	f
139	multisession_30829963	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:45.914843	\N	\N	\N	f
140	endsession_58fb852c	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:45.988786	\N	\N	\N	f
141	activity_f7f46a08	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:46.092442	\N	\N	\N	f
142	findactive_a826fb17	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:46.322078	\N	\N	\N	f
143	loginuser_68f716ff	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:46.414828	\N	2025-12-22 02:20:46.444567	\N	f
144	createsession_d6bf959b	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:46.496502	\N	2025-12-22 02:20:46.595153	\N	f
145	plaintext_test_a97988c3	$2b$12$S4Cn9gdLnh.NIbl0NT4QzOBBAnR4EpMl6ckvzjVAtaTG7K/XW9vxm	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:46.892581	\N	\N	\N	f
146	user1_550d95bb	$2b$12$Zg3g1qiiRtto4sP84tjpAujLjIazZ684QveC4uesXM2r0iBK3QeHy	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:47.408069	\N	\N	\N	f
147	user2_550d95bb	$2b$12$Eer3TeVR4YStYyZ5I69bN.X0HRZKmuZ/a6Gci/RUXbKB4mzMY81ty	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:47.408073	\N	\N	\N	f
148	user_user_1980f7d5	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:47.888561	\N	\N	\N	f
149	admin_user_1980f7d5	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 02:20:47.888564	\N	\N	\N	f
150	superadmin_user_1980f7d5	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-22 02:20:47.888566	\N	\N	\N	f
152	mixed_7952929a_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 02:20:48.009829	\N	\N	\N	f
153	mixed_7952929a_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 02:20:48.009833	\N	\N	\N	f
154	mixed_7952929a_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:48.009835	\N	\N	\N	f
155	mixed_7952929a_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:48.009836	\N	\N	\N	f
156	mixed_7952929a_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 02:20:48.009838	\N	\N	\N	f
157	ldm_test_user	$2b$12$Msr69n.Vtq7tPCPx.l8kf.Ze2wuKS2arW76.mI4z2ru4Hlo//veOS	ldmtest@example.com	LDM Test User	Testing	\N	\N	admin	t	2025-12-22 02:36:52.5838	\N	2025-12-22 02:36:52.896153	\N	f
158	auth_user_1766342096	$2b$12$95mOpuyo1UwN3bYEZPdYEuAKswC5fxx/w6Mw3PZ/7kBzUM8/v4uum	auth_user_1766342096@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 03:34:56.657511	\N	\N	\N	f
159	regular_user_1766342097	$2b$12$LRFchXXAbXnl3i6cJmsyX.XKxLC1kL2jJu8avJgO5B42xpqksa0Ae	regular_1766342097@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 03:34:57.383586	\N	\N	\N	f
160	admin_user_1766342097	$2b$12$OcoHZvPt8INlzGkzl8WPr.kt9SdyTra3H9rUQ6BC8pXsR4W6oz3yK	admin_1766342097@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 03:34:57.583322	\N	\N	\N	f
161	activation_test_1766342097	$2b$12$3K5on2xnrAljpNyfguJxj.nPiwu0whCLh2Scf77Ez1ea.nyGER3AO	activation_1766342097@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 03:34:57.867786	\N	\N	\N	f
162	dept_user_1766342098_0	$2b$12$Ic5w4ny6coAbjtA/mYWrCODLWq3ILh1dSnlablteDzuSyMnKS3sT2	dept_user_1766342098_0@example.com	Dept User 0	TestDept_1766342098	\N	\N	user	t	2025-12-22 03:34:58.274137	\N	\N	\N	f
163	dept_user_1766342098_1	$2b$12$pELTQh/SQeI98coRFJ..6O45HXAdCk7zD/wHjKQlgu8fUvLHaqI96	dept_user_1766342098_1@example.com	Dept User 1	TestDept_1766342098	\N	\N	user	t	2025-12-22 03:34:58.47482	\N	\N	\N	f
164	dept_user_1766342098_2	$2b$12$L.lGOFqqNi1iHUVHU1Rxq.oYIOOu95/KnR7XBtaOITHiINf23Nt4W	dept_user_1766342098_2@example.com	Dept User 2	TestDept_1766342098	\N	\N	user	t	2025-12-22 03:34:58.674993	\N	\N	\N	f
165	unique_test_1766342098	$2b$12$RI9QNAhbbhsgbGDBgQb.N.3M2cNY.sq81Q5OKhHLO8kNHqjeanFma	unique_1766342098@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 03:34:58.922201	\N	\N	\N	f
166	login_test_1766342099	$2b$12$pbuBwi1.tABeWX.Exc3dV.knQTMUmXdCxblTUOHsV.Y7eTSRzepzG	login_test_1766342099@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 03:34:59.244379	\N	2025-12-22 03:34:59.359867	\N	f
167	test_async_1766342099	$2b$12$VeJha.Efw.V/PnSCahv8PuCUl4stvJ9QnXhZ7eJZ7aT5QOkDvP6Ve	test_async_1766342099@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 03:34:59.65807	\N	\N	\N	f
168	auth_test_1766342099	$2b$12$PnPmePApJZ4Mxs.G.Zzuk.gs7XDGAoFSuLNJcOHMF8Drgxsdv1Izu	auth_test_1766342099@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 03:34:59.951093	\N	\N	\N	f
169	log_test_1766342100	$2b$12$aRZHrAF/d1wjzIXrgcfheebf3AFc5DCGELFTtQ9fOT4HmQJ3hb9Q.	log_test_1766342100@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 03:35:00.243977	\N	\N	\N	f
170	session_test_1766342109	$2b$12$42GreQByUwmq9qkId1ve3OxKF/tXvkhqOSAdinOM4/JSGCGuzeOKS	session_test_1766342109@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 03:35:00.106295	\N	\N	\N	f
171	session_update_1766342100	$2b$12$ALfMiGrtuvMgNn2a/Re8EeV0h7i2mZVtlnIFDjCmJ34i7J4h4Cc2y	session_update_1766342100@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 03:35:00.521059	\N	\N	\N	f
172	session_filter_1766342100	$2b$12$EhqfEZYnDeT9LPfFHinApOuPfZlTrZqQqU1IOi2ZbJIPiG1y9W7ay	session_filter_1766342100@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 03:35:01.028433	\N	\N	\N	f
173	hashtest_73fd1467	$2b$12$lLAwaUDkZnhEyBw1NrCNVu6SSKeqX1iI9cZ2UdsPGGPvrclwJXxYW	hash_73fd1467@test.com	\N	\N	\N	\N	user	t	2025-12-22 03:35:01.514444	\N	\N	\N	f
174	admin_test_274eeed3	admin_hash	admin_274eeed3@test.com	\N	\N	\N	\N	admin	t	2025-12-22 03:35:01.77106	\N	\N	\N	f
175	deactivate_69887a2c	hash	\N	\N	\N	\N	\N	user	f	2025-12-22 03:35:01.830847	\N	\N	\N	f
176	sessiontest_4971ee29	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:01.911897	\N	\N	\N	f
177	multisession_c1cf6401	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:01.99558	\N	\N	\N	f
178	endsession_29023c19	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:02.07855	\N	\N	\N	f
179	activity_a9136657	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:02.183197	\N	\N	\N	f
180	findactive_a0f91e97	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:02.397076	\N	\N	\N	f
181	loginuser_d0688ca5	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:02.4822	\N	2025-12-22 03:35:02.50792	\N	f
182	createsession_8fd7da02	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:02.565776	\N	2025-12-22 03:35:02.59092	\N	f
183	plaintext_test_6fbf38a0	$2b$12$.WW3XAwmUtDBnUC3tg8XLe94dwo8P1unWuP6WcdNxdsmzaFHI74Fi	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:02.858613	\N	\N	\N	f
184	user1_4ecfe092	$2b$12$58o0.qD9zYREw1foJBh3ku1h6AhKZqfuVmSEXuR1.apeJvYI8d.Ym	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:03.371389	\N	\N	\N	f
185	user2_4ecfe092	$2b$12$nmCVdeyDsQkqp30jfyDC3eS1cc9qiBUKd6VT55CBB7KrCUsPfJ2qq	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:03.371393	\N	\N	\N	f
186	user_user_8fdbd4a1	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:03.835195	\N	\N	\N	f
187	admin_user_8fdbd4a1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 03:35:03.835199	\N	\N	\N	f
188	superadmin_user_8fdbd4a1	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-22 03:35:03.835201	\N	\N	\N	f
189	norole_b2b536cf	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:03.905407	\N	\N	\N	f
190	mixed_5b5502d1_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 03:35:03.963003	\N	\N	\N	f
191	mixed_5b5502d1_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 03:35:03.963008	\N	\N	\N	f
192	mixed_5b5502d1_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:03.96301	\N	\N	\N	f
193	mixed_5b5502d1_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:03.963011	\N	\N	\N	f
194	mixed_5b5502d1_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:03.963013	\N	\N	\N	f
195	auth_user_1766342147	$2b$12$zLvFTGsNaoP4qS6Tfxtu0.v0YSB4GEd2d3pHuJhhoD4JpGClgxcV.	auth_user_1766342147@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 03:35:47.391795	\N	\N	\N	f
196	regular_user_1766342147	$2b$12$LmJoNNIjuDu4BqZv79wQceEfqUJqoYnC3FLzJ4y1vCC3mjbB49DHS	regular_1766342147@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 03:35:48.084666	\N	\N	\N	f
197	admin_user_1766342147	$2b$12$yOj2u8tumNZf0TBwogCDa.U.XMhHrJgnGH9SESGDf4zhK9VdUHCZe	admin_1766342147@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 03:35:48.286925	\N	\N	\N	f
202	unique_test_1766342149	$2b$12$lb/qZL7ZZPY1/LxE.iuGw.7PfU150Og7y.nYgX.froFG2WA3hh7Y6	unique_1766342149@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 03:35:49.649899	\N	\N	\N	f
198	activation_test_1766342148	$2b$12$GOR1W26k0aQ4/9.s6oq7Eu1D/n.u0hWw95NfBZBe0CZvG01hT7GZC	activation_1766342148@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 03:35:48.600602	\N	\N	\N	f
199	dept_user_1766342148_0	$2b$12$P1d5639KAvARN9kPVMl6X.3KLg5S8sZNC4Z6oIrZ59SfZe7lQ9lY2	dept_user_1766342148_0@example.com	Dept User 0	TestDept_1766342148	\N	\N	user	t	2025-12-22 03:35:48.998987	\N	\N	\N	f
200	dept_user_1766342148_1	$2b$12$2cMwSPUitQfnDt0lMlZCi.ok6aVekytfMi9kE79ugLUvK9TfCJoAO	dept_user_1766342148_1@example.com	Dept User 1	TestDept_1766342148	\N	\N	user	t	2025-12-22 03:35:49.203854	\N	\N	\N	f
201	dept_user_1766342148_2	$2b$12$N3nfsdUUBcEKCJzDknM1cOn/5sVW/ylYhKRt5ENu.Qwdh5WUVvZVC	dept_user_1766342148_2@example.com	Dept User 2	TestDept_1766342148	\N	\N	user	t	2025-12-22 03:35:49.406348	\N	\N	\N	f
203	login_test_1766342149	$2b$12$fuiE6nowm105Pi50lFYLRu3tmEx1wt7MijqrquZ6dkSrhj/7GDKZG	login_test_1766342149@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 03:35:49.954216	\N	2025-12-22 03:35:50.028964	\N	f
204	test_async_1766342150	$2b$12$iVY0Q99tiT/x5tlJNy1fz.wDI2j0UBbDamNUoi7wiKoh.y0iZ6rYO	test_async_1766342150@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 03:35:50.31049	\N	\N	\N	f
205	auth_test_1766342159	$2b$12$OpmkCebqPQhos.UAh.zLLeHxx7RK4BUvKA8nl6IBm1x2fU3V5R9Gu	auth_test_1766342159@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 03:35:59.281224	\N	\N	\N	f
206	log_test_1766342150	$2b$12$E2u8H7mGh4igp145NrxlJuG7zZ1wj3iWHIOkiQswRomUYayJqzxTa	log_test_1766342150@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 03:35:50.447895	\N	\N	\N	f
207	session_test_1766342150	$2b$12$Np.urS48TuNIg5BKQm5FkeTXqANDtjaz3j3ecwkWzfBlByXKYEex2	session_test_1766342150@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 03:35:50.917835	\N	\N	\N	f
208	session_update_1766342151	$2b$12$n9KDOP2wUKliPkBT0UYxHeXxdGuZaDIXgIX8M2tWkwDbNisRexC4W	session_update_1766342151@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 03:35:51.387481	\N	\N	\N	f
209	session_filter_1766342152	$2b$12$RFWTD0/cXxS.wWw0DC4uaujDL.oUpZK6t2XVtKbt2jKYua1nomCkS	session_filter_1766342152@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 03:35:52.445253	\N	\N	\N	f
210	hashtest_26f54491	$2b$12$z7YHr6nCDBCVlr7cvka4OObJGgexmuI8TM2cF/uC0pTakUnjFnd8G	hash_26f54491@test.com	\N	\N	\N	\N	user	t	2025-12-22 03:35:52.811427	\N	\N	\N	f
211	admin_test_9301f3cd	admin_hash	admin_9301f3cd@test.com	\N	\N	\N	\N	admin	t	2025-12-22 03:35:53.099434	\N	\N	\N	f
212	deactivate_f82b0018	hash	\N	\N	\N	\N	\N	user	f	2025-12-22 03:35:53.160266	\N	\N	\N	f
213	sessiontest_af9165c1	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:53.255261	\N	\N	\N	f
214	multisession_4670bc3a	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:53.342543	\N	\N	\N	f
215	endsession_80cf8d57	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:53.436881	\N	\N	\N	f
216	activity_6f47d8f9	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:53.554599	\N	\N	\N	f
217	findactive_baae9a66	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:53.829917	\N	\N	\N	f
218	loginuser_49aba722	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:53.997144	\N	2025-12-22 03:35:54.054988	\N	f
219	createsession_17ec779c	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:54.12262	\N	2025-12-22 03:35:54.154485	\N	f
220	plaintext_test_4e5897c7	$2b$12$JgnMv2t8wd1tYI/KTw1nfut/RZsCl7fOWfl30ORRhfSJoiIbpC0M.	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:54.416795	\N	\N	\N	f
221	user1_2921c862	$2b$12$pgKVfksLaiHIeZs4E7yP6eN/f8nXwPdXvv7E1J.eDTedn7BFFWpy2	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:54.890773	\N	\N	\N	f
222	user2_2921c862	$2b$12$P4AAfPmuMZpGcmLqbWUumOnX5VmNq44PDMfN1q3F5oDe1WB0DtgBq	\N	\N	\N	\N	\N	user	t	2025-12-22 03:35:54.890778	\N	\N	\N	f
223	user_user_74bb1fa1	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:36:04.076113	\N	\N	\N	f
224	admin_user_74bb1fa1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 03:36:04.076117	\N	\N	\N	f
225	superadmin_user_74bb1fa1	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-22 03:36:04.076118	\N	\N	\N	f
226	norole_e6f31f34	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:36:04.150863	\N	\N	\N	f
227	mixed_4d001ce1_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 03:36:04.211678	\N	\N	\N	f
228	mixed_4d001ce1_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 03:36:04.211682	\N	\N	\N	f
229	mixed_4d001ce1_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:36:04.211684	\N	\N	\N	f
230	mixed_4d001ce1_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:36:04.211685	\N	\N	\N	f
231	mixed_4d001ce1_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 03:36:04.211687	\N	\N	\N	f
232	auth_user_1766347356	$2b$12$zFh9Yjoil1TlpZw/3q3crui2wIu0KkrI6M1fPxCuudBNu4AZTZlNC	auth_user_1766347356@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 05:02:36.622108	\N	\N	\N	f
233	regular_user_1766347357	$2b$12$ERKHvlf8sPSwyWfjEzz04erfAj36fWTY6/22je.ja3RJGGOuLo3cG	regular_1766347357@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 05:02:37.328629	\N	\N	\N	f
234	admin_user_1766347357	$2b$12$6POquJZGdhxLJrViJ4Q61e2J8GykB/1WsB5pMapCPtPY/OcTPh1JO	admin_1766347357@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 05:02:37.534391	\N	\N	\N	f
251	dept_user_1766347400_0	$2b$12$Fkt.50TxtS0VAqXOIcu81OIE0OwJi2YdCfdUU8EGwNP5W.5xbwq7C	dept_user_1766347400_0@example.com	Dept User 0	TestDept_1766347400	\N	\N	user	t	2025-12-22 05:03:20.338093	\N	\N	\N	f
235	activation_test_1766347357	$2b$12$k/PO/qd6pYVebgaDjjAfBudBYdNrbd.X5qrwiFl9ZW6/JBx4pKsZi	activation_1766347357@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 05:02:37.824838	\N	\N	\N	f
236	dept_user_1766347358_0	$2b$12$/YktgwTfSvZeRqwoORFXPed6G986CQpL1dOA3pmPCJukT4JJR5VZC	dept_user_1766347358_0@example.com	Dept User 0	TestDept_1766347358	\N	\N	user	t	2025-12-22 05:02:38.233609	\N	\N	\N	f
237	dept_user_1766347358_1	$2b$12$KLZ0jWXtCYUNg2XRnqhN2.kIJKelKvxrwjxu3Z.ZBng8qyFQpY1.2	dept_user_1766347358_1@example.com	Dept User 1	TestDept_1766347358	\N	\N	user	t	2025-12-22 05:02:38.439531	\N	\N	\N	f
238	dept_user_1766347358_2	$2b$12$ZNfiKwZpr4OfdhfIPSoy4eY79QIUKeO.19HB7SMreRsI9RtIAozyG	dept_user_1766347358_2@example.com	Dept User 2	TestDept_1766347358	\N	\N	user	t	2025-12-22 05:02:38.645033	\N	\N	\N	f
239	unique_test_1766347358	$2b$12$HYApBS1v5fnXUmKkSQ7TAeK1mn8oydrRP7j1yWG1jwNtaNFEjnmy2	unique_1766347358@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 05:02:47.647081	\N	\N	\N	f
240	login_test_1766347367	$2b$12$VcAFaHUNUG1SEk0qb6sQa.wq3yflnVlees8/4miEqrEaR4IsG9dSy	login_test_1766347367@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 05:02:38.682534	\N	2025-12-22 05:02:38.897469	\N	f
241	test_async_1766347359	$2b$12$uHqM1nEw6MhYG2lVjWur5.wgPo7Xdu9C31F3jnvSbPyAF5gO2/hw2	test_async_1766347359@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 05:02:39.21987	\N	\N	\N	f
242	auth_test_1766347359	$2b$12$i9hn.7lUEkr3ilcpDnW1Muszq5ESRhq9Mmpn5sRRwcmMxMr3MLhYe	auth_test_1766347359@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 05:02:39.546973	\N	\N	\N	f
243	log_test_1766347359	$2b$12$Ofr4Sb.BbYgh86i/1BhfI.ABELtygLeTHqe2Oe80GJ05cSD.JhtrG	log_test_1766347359@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 05:02:39.831279	\N	\N	\N	f
244	session_test_1766347360	$2b$12$wEVyxmfwLYioB1Y.adaNVOCH3.nrElQM7qba64yjUYIHr3AoFHoce	session_test_1766347360@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 05:02:40.215161	\N	\N	\N	f
245	session_update_1766347360	$2b$12$FxYMlk5e6Du11/58vcn1zeI/m4RuUA5aHbC//FZP9VD9uetGj7LIK	session_update_1766347360@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 05:02:40.591344	\N	\N	\N	f
246	session_filter_1766347360	$2b$12$jJHXtuKedMBvPqJ3woaCVeLGEq6OoUdXMrvYcySdKPJi1Srp8phwO	session_filter_1766347360@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 05:02:41.017221	\N	\N	\N	f
247	auth_user_1766347407	$2b$12$q5El0EFIgDShBlBBkN/BSOmEFD7KKkYOkt01Xt8TMda6DqD4nppkC	auth_user_1766347407@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 05:03:18.68728	\N	\N	\N	f
248	regular_user_1766347399	$2b$12$Exxygf7BAfCw0ePCHAMGJuYgDKuL5dPbChYifQ5viXEjABJ.ckYfC	regular_1766347399@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 05:03:19.424542	\N	\N	\N	f
249	admin_user_1766347399	$2b$12$nEelXUmsBw6IUIgevGkBqeAYc53hi8h01wXMt4q2oOMTrqUytvOcy	admin_1766347399@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 05:03:19.62437	\N	\N	\N	f
252	dept_user_1766347400_1	$2b$12$utxi1xMCupvkCSbEx1Ft6uAsl4DBps0kxCCXeVL9K5QxEZagR8uS.	dept_user_1766347400_1@example.com	Dept User 1	TestDept_1766347400	\N	\N	user	t	2025-12-22 05:03:20.538009	\N	\N	\N	f
250	activation_test_1766347399	$2b$12$E8oQxIE4M55QYL5i6W7mieCaOZP15t.2Zl1GBfD3NQD2vixas3/DK	activation_1766347399@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 05:03:19.964132	\N	\N	\N	f
253	dept_user_1766347400_2	$2b$12$iZQDaMdTQUKFrGUKEp4uoOZwXpKJm68tQbjZfAVB8jDdDuX0pVjYm	dept_user_1766347400_2@example.com	Dept User 2	TestDept_1766347400	\N	\N	user	t	2025-12-22 05:03:20.739109	\N	\N	\N	f
254	unique_test_1766347400	$2b$12$A9mdV7pbbh.fILyYTAe9xu/cKEbFfJ8OJZZexjsrsz709hGc6w5eK	unique_1766347400@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 05:03:20.99039	\N	\N	\N	f
255	login_test_1766347401	$2b$12$7D4ZSzBJxRKXH1NR4uSYHesYO18J0OBz771bL01PwExDpjO3cx5HK	login_test_1766347401@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 05:03:21.272201	\N	2025-12-22 05:03:21.346505	\N	f
256	test_async_1766347401	$2b$12$A8xJB/eoKiGt5ZA4oDOLAOMnSRbkeNb1oBAGb8fsDH8nvzVP9xTre	test_async_1766347401@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 05:03:21.633376	\N	\N	\N	f
257	auth_test_1766347401	$2b$12$zgN8JhuMPTze8Z2OS0PWXeQ3gl4enMtUnjabuG7Oj1FjC35Z/5xb2	auth_test_1766347401@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 05:03:21.993818	\N	\N	\N	f
258	log_test_1766347402	$2b$12$f5t3lLSQ9QHrla2LuIK8WeFGk.xsCasXB5pSg.v5J0U4TagwHItWi	log_test_1766347402@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 05:03:22.282583	\N	\N	\N	f
259	session_test_1766347402	$2b$12$T0G5V.02N4AzXr14gGi5a.ht.fB.cJkIRQxgZ.HPqFbPPGQ4sKdu.	session_test_1766347402@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 05:03:22.642218	\N	\N	\N	f
366	superadmin_user_cc7b83ff	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-22 05:31:59.370745	\N	\N	\N	f
260	session_update_1766347402	$2b$12$4ApuNmmhzN8ozfWTiU9X.u/QC.BQOKJQXiSNDAOQqqiAUVExRCgHC	session_update_1766347402@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 05:03:23.013755	\N	\N	\N	f
261	session_filter_1766347403	$2b$12$uv8owUHWZL48MuXjCVepKu/SUX3Q8OMg/X.K0tsHSQ6sxFMoMpb3S	session_filter_1766347403@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 05:03:23.369869	\N	\N	\N	f
262	auth_user_1766348706	$2b$12$Rh3c5n4OerDfGGZbgSlwN.sw86w9X2wbwDnaGDk9hdm5KrkOt4vom	auth_user_1766348706@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 05:25:06.236112	\N	\N	\N	f
263	regular_user_1766348706	$2b$12$3jDUcNuZUknlYjkQBkthcexqXzgUIzpAl9OeRaqZl.lm123xq4wm6	regular_1766348706@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 05:25:06.992077	\N	\N	\N	f
264	admin_user_1766348706	$2b$12$ndCXb6NbwVZU8TS156eQPuyBH5QPjs9L2EQ0/EheEal3yMyQTmV.O	admin_1766348706@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 05:25:07.194921	\N	\N	\N	f
265	activation_test_1766348707	$2b$12$eJynrGXf7KXliKHm4VGPau.3XSJArDf31bNfudZSe1dmB3m3LBcMi	activation_1766348707@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 05:25:07.956149	\N	\N	\N	f
266	dept_user_1766348708_0	$2b$12$8pGeWUKoHsAJGWETk6L5depmuJ7.uy0lEOvjtzD9gF5R6YuhzlTem	dept_user_1766348708_0@example.com	Dept User 0	TestDept_1766348708	\N	\N	user	t	2025-12-22 05:25:08.466855	\N	\N	\N	f
267	dept_user_1766348708_1	$2b$12$PAqInckalkuOM7KvasTHGeA4ofkYZYpBuq9MPTQvjNlAX1BRJbnny	dept_user_1766348708_1@example.com	Dept User 1	TestDept_1766348708	\N	\N	user	t	2025-12-22 05:25:08.67236	\N	\N	\N	f
268	dept_user_1766348708_2	$2b$12$90a.1o6rwok8hUMIabEF6eVpsEwKDA2sFUHmHLDbbdUfefVIgA9.O	dept_user_1766348708_2@example.com	Dept User 2	TestDept_1766348708	\N	\N	user	t	2025-12-22 05:25:08.876203	\N	\N	\N	f
269	unique_test_1766348708	$2b$12$u3Serk0jkj7h0XRPg46jX.KI3imVgfeIPmmkCnds2vkzEO9LTzUVi	unique_1766348708@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 05:25:09.127924	\N	\N	\N	f
270	login_test_1766348709	$2b$12$S32aFRhmZ5lkcGgWjfQ9AOupsS0ZzeWw4w0bhhG1eXTxOOyJw5jBG	login_test_1766348709@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 05:25:09.422436	\N	2025-12-22 05:25:09.503397	\N	f
271	test_async_1766348709	$2b$12$v4nqtCil0SV248pWIeI22eArHUckB0m4iI6B861gkxKaMYuw3JKr2	test_async_1766348709@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 05:25:09.803266	\N	\N	\N	f
272	auth_test_1766348709	$2b$12$5IF.ocVoRWHaAredaXNcaOxpSMZSwYxkrzNm91iFHtCQ96tWAsAxu	auth_test_1766348709@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 05:25:10.097974	\N	\N	\N	f
273	log_test_1766348710	$2b$12$oezMVebytNvuWu6gRQt8r.8eUez9y1ZApTzVacM8S4TyBbxUKoilO	log_test_1766348710@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 05:25:10.455419	\N	\N	\N	f
274	session_test_1766348710	$2b$12$6YQ0eGE2bbj86mpYBnnFhekwQ9pRALkHujmUoFVJj8JF72d7kLYxO	session_test_1766348710@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 05:25:10.837947	\N	\N	\N	f
275	session_update_1766348719	$2b$12$F7lETxGv2EaWXYd8ey0wsePOCeWNeX3Zg/0QNRHwW86StKJ1F3L/.	session_update_1766348719@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 05:25:19.995707	\N	\N	\N	f
276	session_filter_1766348711	$2b$12$iW9UAMiVoRSWQW62OMhQyuXmgoKPUyD/7DHwSaPUplH0/dXsGn5Iy	session_filter_1766348711@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 05:25:11.207818	\N	\N	\N	f
277	hashtest_936c61f7	$2b$12$x2VKhMxqYitpbCpQYjybW.TggfpFt7bi7geXsSdNpa87DWYRvmhOK	hash_936c61f7@test.com	\N	\N	\N	\N	user	t	2025-12-22 05:25:11.631037	\N	\N	\N	f
278	admin_test_c55dfda3	admin_hash	admin_c55dfda3@test.com	\N	\N	\N	\N	admin	t	2025-12-22 05:25:11.933018	\N	\N	\N	f
279	deactivate_f4e9babd	hash	\N	\N	\N	\N	\N	user	f	2025-12-22 05:25:12.011295	\N	\N	\N	f
280	sessiontest_f09043b8	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:12.100853	\N	\N	\N	f
281	multisession_2e3b65bb	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:12.204146	\N	\N	\N	f
282	endsession_7258ae07	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:12.297532	\N	\N	\N	f
283	activity_ea5d8ac3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:12.423647	\N	\N	\N	f
284	findactive_87b63827	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:12.662042	\N	\N	\N	f
285	loginuser_b16a4024	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:12.755067	\N	2025-12-22 05:25:12.784818	\N	f
286	createsession_1de021e4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:12.849117	\N	2025-12-22 05:25:12.876814	\N	f
287	plaintext_test_8e9df08a	$2b$12$v.Jeiwk57VknXZskfQFHreYff8DLaTNPflYyCd6B/ruJy9QiIzuYK	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:13.152412	\N	\N	\N	f
288	user1_9a16d9b7	$2b$12$8y.9eLTxOsaREQZ9JENT6OssYwskrKutgiji0UPTH7mOHO44bKrWO	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:13.632413	\N	\N	\N	f
289	user2_9a16d9b7	$2b$12$ArC7oWnIl//jZeDUHRHeJ.what5E28KxYvG4CA.leslrzGbQg.HHq	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:13.632418	\N	\N	\N	f
290	user_user_fd6d7861	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:14.117856	\N	\N	\N	f
291	admin_user_fd6d7861	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:25:14.11786	\N	\N	\N	f
292	superadmin_user_fd6d7861	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-22 05:25:14.117862	\N	\N	\N	f
293	norole_aa535d5a	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:14.196926	\N	\N	\N	f
294	mixed_8e9b3082_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:25:14.267115	\N	\N	\N	f
295	mixed_8e9b3082_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:25:14.267119	\N	\N	\N	f
296	mixed_8e9b3082_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:14.267121	\N	\N	\N	f
297	mixed_8e9b3082_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:14.267122	\N	\N	\N	f
298	mixed_8e9b3082_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:25:14.267124	\N	\N	\N	f
299	auth_user_1766348983	$2b$12$iKdwUFM6W0ZAGBfQizOkKO/VLvlnVTgNDpNVs05iTYozQwQdADmlu	auth_user_1766348983@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 05:29:43.868686	\N	\N	\N	f
300	regular_user_1766348984	$2b$12$vGKV1B1Ah4ZZBZGd5BmC2etOxUwyYJwpB41PV27lEg8eaXjVkykTu	regular_1766348984@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 05:29:44.578225	\N	\N	\N	f
301	admin_user_1766348984	$2b$12$0SQsPkr5xz23r8mdT1SC6OWN3MmCY1RrIIkTP4rX9y/Fi04XwwQxu	admin_1766348984@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 05:29:44.780472	\N	\N	\N	f
306	unique_test_1766348985	$2b$12$.ZUHc1nJE2sevI.3fDD3CuhVNpMrsN9WoqdrDdRCBIK0sW4WeCDhi	unique_1766348985@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 05:29:46.161932	\N	\N	\N	f
302	activation_test_1766348984	$2b$12$B.ab1gt9DDVaHJkVEy5TBucsWTMpoiOlQIds2Fhp12Sz76HnXoNZa	activation_1766348984@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 05:29:45.075938	\N	\N	\N	f
303	dept_user_1766348985_0	$2b$12$DlqksV4kZEkXTIPR3aBLeORlL9m6ri2UraBShsI.JAThi6K5dIexS	dept_user_1766348985_0@example.com	Dept User 0	TestDept_1766348985	\N	\N	user	t	2025-12-22 05:29:45.498572	\N	\N	\N	f
304	dept_user_1766348985_1	$2b$12$1RzQB/QiXkG/PpEXLPU3S.JQ5pLYMI2Yt3v/ed3RzsTT/PxTwuLOm	dept_user_1766348985_1@example.com	Dept User 1	TestDept_1766348985	\N	\N	user	t	2025-12-22 05:29:45.703278	\N	\N	\N	f
305	dept_user_1766348985_2	$2b$12$V3yh7FAdwtmWICcW3I5jVuVcFIT.TemEPyU7VVVfqLsQt8E7hempm	dept_user_1766348985_2@example.com	Dept User 2	TestDept_1766348985	\N	\N	user	t	2025-12-22 05:29:45.907402	\N	\N	\N	f
307	login_test_1766348986	$2b$12$0YYPonjosniT6uifoJPUuukTtiOp7UKTJdiZKlQNNnKrltlpKmTMe	login_test_1766348986@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 05:29:55.24571	\N	2025-12-22 05:29:55.361385	\N	f
308	test_async_1766348995	$2b$12$.YRLnwRy9FmzUoSGeLq/ze9Luc6PrLQCpKaJ6FsB.kASUza2LYrEK	test_async_1766348995@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 05:29:46.401106	\N	\N	\N	f
367	norole_be695ea8	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:59.446995	\N	\N	\N	f
368	mixed_e20f08c7_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:31:59.509877	\N	\N	\N	f
309	auth_test_1766348986	$2b$12$0HzLji1X9rgK5fxIUKIY4eeoJsXoUd3xzCQs/3gy3G40Zy3UdAmJG	auth_test_1766348986@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 05:29:46.705432	\N	\N	\N	f
310	log_test_1766348986	$2b$12$9OvTOQjhoSn3/an87KQYn.VxR/ujqnEI3N5iqfzS7DxWgui6DK5y2	log_test_1766348986@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 05:29:47.028653	\N	\N	\N	f
311	session_test_1766348987	$2b$12$IP7GUVvMSJEMZ1HB3MNSR.6Ns1ador8jXsUno5fYELIh4N3Lah43q	session_test_1766348987@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 05:29:47.908681	\N	\N	\N	f
312	session_update_1766348988	$2b$12$IFlrL3Eg0qDTEKmE9xHJzuEq4mYMOl9iGO3XihU7J1e5zFstsyOeC	session_update_1766348988@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 05:29:48.35186	\N	\N	\N	f
313	session_filter_1766348988	$2b$12$0Imz47ylY5mZQw6ul1773urEt3UjP1ehAsw.jpJKrY1TRPkGL.Uqy	session_filter_1766348988@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 05:29:48.758285	\N	\N	\N	f
314	hashtest_ba0b6208	$2b$12$KWUeG6Tlna.Q4HH1GyL3hOIZSPYB0E64wAH6Pr3ff03oKDrjmftNS	hash_ba0b6208@test.com	\N	\N	\N	\N	user	t	2025-12-22 05:29:49.121806	\N	\N	\N	f
315	admin_test_81ee3370	admin_hash	admin_81ee3370@test.com	\N	\N	\N	\N	admin	t	2025-12-22 05:29:49.400016	\N	\N	\N	f
316	deactivate_2236efb0	hash	\N	\N	\N	\N	\N	user	f	2025-12-22 05:29:49.478935	\N	\N	\N	f
317	sessiontest_dc897876	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:49.579627	\N	\N	\N	f
318	multisession_ba547928	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:49.754931	\N	\N	\N	f
319	endsession_bea0aab7	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:49.924094	\N	\N	\N	f
320	activity_454f3297	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:50.128856	\N	\N	\N	f
321	findactive_f611748f	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:50.486481	\N	\N	\N	f
322	loginuser_ca0efa6c	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:50.590299	\N	2025-12-22 05:29:50.628692	\N	f
323	createsession_a5c73a45	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:50.691698	\N	2025-12-22 05:29:50.729214	\N	f
324	plaintext_test_b8d4bd96	$2b$12$FUHsu5qd.DTa/SPLA3QJh.TKHyThzB21o9FYFfmX4BHE1ICYRiNra	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:51.007032	\N	\N	\N	f
325	user1_1409ff92	$2b$12$mRC.d50x3LJDUA6ROCCF7uX6RL2zwF6jj.ZeTUtD2l0ujPOsf9yHi	\N	\N	\N	\N	\N	user	t	2025-12-22 05:30:00.268221	\N	\N	\N	f
326	user2_1409ff92	$2b$12$v92w/UoKrikjXYQZSCqMMetlgv7R4vr/7ySIkIc9Zte1DKrOi5uC2	\N	\N	\N	\N	\N	user	t	2025-12-22 05:30:00.268225	\N	\N	\N	f
327	user_user_ba20f693	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:51.510284	\N	\N	\N	f
328	admin_user_ba20f693	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:29:51.510288	\N	\N	\N	f
329	superadmin_user_ba20f693	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-22 05:29:51.51029	\N	\N	\N	f
330	norole_a6b41b0a	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:51.638346	\N	\N	\N	f
331	mixed_7af32ba1_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:29:51.742462	\N	\N	\N	f
332	mixed_7af32ba1_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:29:51.742485	\N	\N	\N	f
333	mixed_7af32ba1_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:51.742486	\N	\N	\N	f
334	mixed_7af32ba1_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:51.742488	\N	\N	\N	f
335	mixed_7af32ba1_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:29:51.742489	\N	\N	\N	f
336	auth_user_1766349111	$2b$12$ta.vf6IsfFOuFz5hhYcIluOcYWlz3BA6FYOJMPZ2LZb05oONSp/gu	auth_user_1766349111@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 05:32:00.363007	\N	\N	\N	f
337	regular_user_1766349111	$2b$12$WkM.hfzrtCBA/g6C2MFuMO2aU4gJ.NnNjj0SnUUba2S0Vs2Pp86ym	regular_1766349111@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 05:31:51.830907	\N	\N	\N	f
338	admin_user_1766349111	$2b$12$LBLBnYwoCF.rkBGc9gwad.68FhCmjM5TeT5QpOq9I/4ruYH6yTXfe	admin_1766349111@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 05:31:52.036575	\N	\N	\N	f
351	hashtest_51b68e43	$2b$12$FAg8uebmMxiLaNHKF/st2OBsBWIyECjuz17EP8QJsIuuEyXn1JoIy	hash_51b68e43@test.com	\N	\N	\N	\N	user	t	2025-12-22 05:31:56.531205	\N	\N	\N	f
339	activation_test_1766349112	$2b$12$Rd8egfxZJeWkr7jh0Tcj9.Dr1ULduSzi3JgRVEQWRU1o3SmskqrU6	activation_1766349112@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 05:31:52.357376	\N	\N	\N	f
340	dept_user_1766349112_0	$2b$12$74Ft0jPQeIWZ9UEbBd3LqOynYTBhx3fdITJV.R2dfvg9le5nPBCKG	dept_user_1766349112_0@example.com	Dept User 0	TestDept_1766349112	\N	\N	user	t	2025-12-22 05:31:52.788302	\N	\N	\N	f
341	dept_user_1766349112_1	$2b$12$WYHrGou2PAc923sV3wYHB.VBJ2GrzVHGhAtF3D12PqxvJSk0khgcm	dept_user_1766349112_1@example.com	Dept User 1	TestDept_1766349112	\N	\N	user	t	2025-12-22 05:31:52.993637	\N	\N	\N	f
342	dept_user_1766349112_2	$2b$12$romS8DH5MGpbRNM2JYcwEOJ7zt//pP6yqoMUUnHjOmsrw4IQGSbhu	dept_user_1766349112_2@example.com	Dept User 2	TestDept_1766349112	\N	\N	user	t	2025-12-22 05:31:53.198985	\N	\N	\N	f
343	unique_test_1766349113	$2b$12$ucNfYmvL6n7i5VhzxL5imuvC8A3gH.TseDXWEFQ7rwi5fQZN6b1VW	unique_1766349113@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 05:31:53.47168	\N	\N	\N	f
344	login_test_1766349113	$2b$12$qZnFXlWlGauVGCv6mL3yD.HY0X41T.or6Xsw9Ya5wmgQjqsb7AvXy	login_test_1766349113@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 05:31:53.806042	\N	2025-12-22 05:31:53.894435	\N	f
345	test_async_1766349113	$2b$12$w/VM85yQQ/TpgFAYUtipY.Q2t4ea58whM/XvhfxY04h3u/.dTysaW	test_async_1766349113@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 05:31:54.194951	\N	\N	\N	f
346	auth_test_1766349114	$2b$12$Oj/CMnsSXGFoJOQHaxgdeu5Ga34xMQhwkwe9VFaxPg6hrsdqTLEZS	auth_test_1766349114@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 05:31:54.49676	\N	\N	\N	f
347	log_test_1766349114	$2b$12$KyC0ze.FY2hAQbN9BrW4eeDU9INVn4Yy29jKxTxHfLuyLDhidJF/y	log_test_1766349114@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 05:31:54.792819	\N	\N	\N	f
348	session_test_1766349114	$2b$12$WX.IAvPp0B6JvJ/5TUKP8OJfzi10EMSW3IKebmo5tXxASYYcJPYLy	session_test_1766349114@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 05:31:55.195378	\N	\N	\N	f
349	session_update_1766349115	$2b$12$RHEU4i8B2RPdrT4cpGnBeOygmQMyqkEeyBG0VQu6fMwD1Tgii7fU6	session_update_1766349115@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 05:31:55.584323	\N	\N	\N	f
350	session_filter_1766349115	$2b$12$LsZuqhsXR0MTcHWc7ZPLx.m6jricZAajpqNWyqo0Qfls0N63iR96O	session_filter_1766349115@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 05:31:56.17333	\N	\N	\N	f
352	admin_test_0a6a0a4c	admin_hash	admin_0a6a0a4c@test.com	\N	\N	\N	\N	admin	t	2025-12-22 05:32:05.59134	\N	\N	\N	f
353	deactivate_a80b95e7	hash	\N	\N	\N	\N	\N	user	f	2025-12-22 05:32:05.665477	\N	\N	\N	f
354	sessiontest_7c39a66a	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:56.512288	\N	\N	\N	f
355	multisession_c75f77d0	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:56.649797	\N	\N	\N	f
356	endsession_588a9e3f	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:57.039193	\N	\N	\N	f
357	activity_85fc9608	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:57.302131	\N	\N	\N	f
358	findactive_df175393	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:57.725894	\N	\N	\N	f
359	loginuser_8ff14450	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:57.909568	\N	2025-12-22 05:31:57.994173	\N	f
360	createsession_b309966a	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:58.097094	\N	2025-12-22 05:31:58.137309	\N	f
361	plaintext_test_19e65ec6	$2b$12$ycBHnk/aJKkxMvzYFqLPN.Y5.MzT5Mw.j/ttIy5dv8gV4DQcbXND6	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:58.406346	\N	\N	\N	f
362	user1_b607296f	$2b$12$.sXemMCaCJCxhl06t.gSsu3/1yBsx7n5qRK/nMOFfZVoTQXm691yy	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:58.886016	\N	\N	\N	f
363	user2_b607296f	$2b$12$C/fKP4gL0rbuAIDso9wGWOTzBsZafWo0H6NsOoYuCkd8ibEPA.IVy	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:58.886021	\N	\N	\N	f
364	user_user_cc7b83ff	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:59.370739	\N	\N	\N	f
365	admin_user_cc7b83ff	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:31:59.370743	\N	\N	\N	f
369	mixed_e20f08c7_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:31:59.509881	\N	\N	\N	f
370	mixed_e20f08c7_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:59.509882	\N	\N	\N	f
371	mixed_e20f08c7_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:59.509884	\N	\N	\N	f
372	mixed_e20f08c7_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:31:59.509885	\N	\N	\N	f
373	auth_user_1766350209	$2b$12$RiEKhPNZpfzfX53MchMvaeLw8CrGNqvg8YtqM/vwndicybHv74jc.	auth_user_1766350209@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-22 05:50:09.933791	\N	\N	\N	f
374	regular_user_1766350210	$2b$12$q0YJR7C8KTaTtXdUrvx3O.td.JUGi/PT1ztcqcjLzCqsk3vxMWxji	regular_1766350210@example.com	Regular User	Testing	\N	\N	user	t	2025-12-22 05:50:10.63235	\N	\N	\N	f
375	admin_user_1766350210	$2b$12$EpC/uTXFv4fvGeoqxmfm/uKgbrqrjtsIbAnUvpZ/7kO.C1hNMaury	admin_1766350210@example.com	Admin User	IT	\N	\N	admin	t	2025-12-22 05:50:10.836284	\N	\N	\N	f
411	test_created_595250	$2b$12$6E7U6vll030jwmnvdFkNvuggEm9eOeP0pMXDYHE9NtGoRGouzccmS	\N	\N	\N	\N	\N	user	f	2025-12-24 16:54:19.43442	2	\N	\N	f
376	activation_test_1766350210	$2b$12$hMhaWXTbON34m1ZmkBHS6OJ9TBjX8MzYN/bjrKvDFz86pW5Yfs812	activation_1766350210@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-22 05:50:11.130724	\N	\N	\N	f
377	dept_user_1766350211_0	$2b$12$y.DkFnLnjWR0karj22paa.fvsuFYkJItPh9rOY9Uw1Teo97Z.AMDK	dept_user_1766350211_0@example.com	Dept User 0	TestDept_1766350211	\N	\N	user	t	2025-12-22 05:50:11.532042	\N	\N	\N	f
378	dept_user_1766350211_1	$2b$12$5pmMkwv9eVDH2jhxCr/am.HK.3tpPT.vxBLvZto.Q9QWtsVxyiDz.	dept_user_1766350211_1@example.com	Dept User 1	TestDept_1766350211	\N	\N	user	t	2025-12-22 05:50:11.737593	\N	\N	\N	f
379	dept_user_1766350211_2	$2b$12$guXTRg89Ug0LBSf04Y3DKOcdCi/Vl8oYYJFXBwEiUguQXcuLw30zW	dept_user_1766350211_2@example.com	Dept User 2	TestDept_1766350211	\N	\N	user	t	2025-12-22 05:50:11.941949	\N	\N	\N	f
380	unique_test_1766350211	$2b$12$sKhXHESwUom6LkHj.YeXFuxcanwMTaEyawU3WERE5lkIhlNYaJbRm	unique_1766350211@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-22 05:50:12.187338	\N	\N	\N	f
381	login_test_1766350212	$2b$12$pw6/VHw5Vi2AKskZGlX8XO15bjeqpD6Jd/..vv37AqvKcrqVPZPbO	login_test_1766350212@example.com	Login Test	Testing	\N	\N	user	t	2025-12-22 05:50:12.477704	\N	2025-12-22 05:50:12.558761	\N	f
382	test_async_1766350212	$2b$12$dMYFbrpzH3WkX6QGRDbsUOEeE35jObZN5K7vIb98Y9U3oZMCEzug2	test_async_1766350212@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-22 05:50:12.859293	\N	\N	\N	f
383	auth_test_1766350212	$2b$12$t8RW.5gYxrZ8Mh2Eb2XTTO6DJCugOpq9Q8Z4LaivITYg5vLwovQUW	auth_test_1766350212@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-22 05:50:13.145581	\N	\N	\N	f
384	log_test_1766350213	$2b$12$t/7a9cTHAGN9qanKKwr.v.pD5pfNZw3chjJPMNqD4rodohYuSSsce	log_test_1766350213@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-22 05:50:22.244684	\N	\N	\N	f
385	session_test_1766350222	$2b$12$c9AdE6/XCwqr.hIbvSiHJ.SxFSiaoLNitZOvmF2qQy.A.uEZSXSBy	session_test_1766350222@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-22 05:50:13.323753	\N	\N	\N	f
386	session_update_1766350213	$2b$12$eTBVsOrMI/wMJ.iqO8eoROrrIfjPueNoyF97u1EpRJl/G8YfBCPJS	session_update_1766350213@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-22 05:50:14.012511	\N	\N	\N	f
387	session_filter_1766350214	$2b$12$vzirLRzkTCVJgwFMAtQtWeS0FJFZpxdrcG5oPUlAKIsACGNwUQwAy	session_filter_1766350214@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-22 05:50:14.663877	\N	\N	\N	f
388	hashtest_9ab72924	$2b$12$E.OPev9m8pexDmGfk/ke0OhaIui5H06nySxB.gcqsewzhwzo5r8Iy	hash_9ab72924@test.com	\N	\N	\N	\N	user	t	2025-12-22 05:50:15.018427	\N	\N	\N	f
389	admin_test_cb281854	admin_hash	admin_cb281854@test.com	\N	\N	\N	\N	admin	t	2025-12-22 05:50:15.295233	\N	\N	\N	f
390	deactivate_a33e7e92	hash	\N	\N	\N	\N	\N	user	f	2025-12-22 05:50:15.384203	\N	\N	\N	f
391	sessiontest_1ddb3810	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:15.543842	\N	\N	\N	f
392	multisession_f901d8d0	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:15.72232	\N	\N	\N	f
393	endsession_644a7736	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:15.889861	\N	\N	\N	f
394	activity_4e7b6da3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:16.080862	\N	\N	\N	f
395	findactive_5b83e03e	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:16.308692	\N	\N	\N	f
396	loginuser_61890941	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:16.401817	\N	2025-12-22 05:50:16.432008	\N	f
397	createsession_cf5004c6	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:16.496618	\N	2025-12-22 05:50:16.523596	\N	f
398	plaintext_test_95e8bca0	$2b$12$5OE8p8EkLTNWggMvN3Ix.u68TXVOh0Tlf6APVrtnf6HbV4V2ycS9q	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:16.78938	\N	\N	\N	f
399	user1_27f42877	$2b$12$jXGoyxWTzFyj9kKrTKJm0u0i9m30F.uATECQ3Ap.aEdpLVcu7KECq	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:17.26588	\N	\N	\N	f
400	user2_27f42877	$2b$12$faUh90V6o58fORAQNXUS1OhYSPTdlIAPK1hUF32BuI/B7G6ykVE8e	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:17.265885	\N	\N	\N	f
401	user_user_5ebf75a6	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:17.745976	\N	\N	\N	f
402	admin_user_5ebf75a6	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:50:17.745981	\N	\N	\N	f
403	superadmin_user_5ebf75a6	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-22 05:50:17.745982	\N	\N	\N	f
404	norole_c432d053	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:17.823983	\N	\N	\N	f
405	mixed_610f6c48_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:50:17.886336	\N	\N	\N	f
406	mixed_610f6c48_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-22 05:50:17.88634	\N	\N	\N	f
407	mixed_610f6c48_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:17.886342	\N	\N	\N	f
408	mixed_610f6c48_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:17.886343	\N	\N	\N	f
409	mixed_610f6c48_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-22 05:50:17.886345	\N	\N	\N	f
410	test_profile_595250	$2b$12$b7s8K/ugwqg790x1xkw2QO2yTPX2XmemcaZYXDewDuDwrVj1U4TI.	\N	Test User	\N	Team Alpha	Japanese	user	f	2025-12-24 16:54:18.864391	2	\N	\N	f
412	test_fullprof_595250	$2b$12$VfwsrqHBeGww2KbMihlU/OmMGCn8FQRUOaO7AROu1etuK3dJV.Tvi	test_595250@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2025-12-24 16:54:23.943883	2	\N	\N	f
413	ci_tester	$2b$12$pJjlxyz8VUY33XL3fApwjOVMYbnzhx8/zaPXfkjd7RvN527cv5A3a	\N	\N	\N	\N	\N	user	t	2025-12-25 06:45:45.470546	\N	\N	\N	f
1	neil	$2b$12$Swrqc488KLpkcD6ZQnYgwOWortma80AGqixihcgvc8CYGuXbK9gkS	neil@locanext.local	Neil Schmitt	\N	CD	EN	admin	f	2025-12-15 15:53:44.99139	\N	2025-12-31 04:22:09.43167	\N	f
428	login_test_1766820951	$2b$12$is0MskwruX21kuRFnit7fue0KB5olERLN.mOjPMLdI7HBJxrR1JDW	login_test_1766820951@example.com	Login Test	Testing	\N	\N	user	t	2025-12-27 16:35:51.97259	\N	2025-12-27 16:35:52.039274	\N	f
417	test_profile_853329	$2b$12$Wv6ia.al0VG0JyCBcAzPKOjJK5CJqQjUXJn9Ucye8nDHKu3Jv3AIC	\N	Test User	\N	Team Alpha	Japanese	user	f	2025-12-27 16:35:39.886955	2	\N	\N	f
429	test_async_1766820952	$2b$12$sxYiS8nYQHmpBfbi8n9sseThr13d/QehzjbGnmzOXmcS2EOCr1QAa	test_async_1766820952@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-27 16:35:52.298938	\N	\N	\N	f
418	test_created_853329	$2b$12$86my9YnXie/c1uR8UrjO7OqjwPp1F44cQvsm66BkFTSrQHBl7lmMO	\N	\N	\N	\N	\N	user	f	2025-12-27 16:35:40.386039	2	\N	\N	f
430	auth_test_1766820952	$2b$12$HTRbp6HUwhq2DDFLEnM0MePAP69rOO6UCMVZDggm957L8SqPAVoMi	auth_test_1766820952@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-27 16:35:52.56143	\N	\N	\N	f
431	log_test_1766820952	$2b$12$KbnsIBSVcOnr8fFZ91BE/eYBPFlrpHHZczzysay3pVfq6ZQL.YQnO	log_test_1766820952@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-27 16:35:52.826811	\N	\N	\N	f
432	session_test_1766820952	$2b$12$rH.WpPnUp5Hs6rkYMIKaTOnXljl5UtZpIv843vqaVXCJjEU9Dj/7.	session_test_1766820952@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-27 16:35:53.161088	\N	\N	\N	f
433	session_update_1766820953	$2b$12$WZbbvpBHDPtJ/2CATNtuPeo3DapJj1ubnJELvDrTyBZerP/9vrsNu	session_update_1766820953@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-27 16:35:53.753503	\N	\N	\N	f
434	session_filter_1766820953	$2b$12$L4wojPOKiqCTUCXpildyguHA/Z50xAasDht2NFe8D20jZCknB378G	session_filter_1766820953@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-27 16:35:54.099552	\N	\N	\N	f
419	test_fullprof_853329	$2b$12$iVEKJBDSjBX4x4WbfueW1.dyD5qdwXtRKNUj5hVF5Y7TTrbj0IbM2	test_853329@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2025-12-27 16:35:44.598044	2	\N	\N	f
435	hashtest_6aea5da8	$2b$12$iSHhxhy5T00eFWeEz4GpvOHsSX//6.nPsX/8pdSiUwmyGUOIpFpoW	hash_6aea5da8@test.com	\N	\N	\N	\N	user	t	2025-12-27 16:35:54.419399	\N	\N	\N	f
414	test_profile_853248	$2b$12$LtOXfWGQ.vkdayYKCAOEoejVbYqWZ3NL2yIpopsWda669pWzfsYRW	\N	Test User	\N	Team Alpha	Japanese	user	f	2025-12-27 16:34:20.616739	2	\N	\N	f
436	admin_test_296a01ec	admin_hash	admin_296a01ec@test.com	\N	\N	\N	\N	admin	t	2025-12-27 16:35:54.665381	\N	\N	\N	f
415	test_created_853248	$2b$12$Cs0AOm2uFeA5wJw118TtiuXe0EhPw68u0pamuu5S5JrOwT2EBDLIG	\N	\N	\N	\N	\N	user	f	2025-12-27 16:34:21.138356	2	\N	\N	f
437	deactivate_6e14022a	hash	\N	\N	\N	\N	\N	user	f	2025-12-27 16:35:54.729746	\N	\N	\N	f
438	sessiontest_92e94202	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:54.799016	\N	\N	\N	f
439	multisession_06f876f6	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:54.870948	\N	\N	\N	f
440	endsession_23f68fc9	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:54.958805	\N	\N	\N	f
416	test_fullprof_853248	$2b$12$AYtOXOBBEozEpjaW.D6sR.LMY6E3hX2p47RtzlTFHonxXq7XC4dDy	test_853248@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2025-12-27 16:34:25.368064	2	\N	\N	f
441	activity_5c36fecc	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:55.060345	\N	\N	\N	f
442	findactive_3842799c	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:55.261607	\N	\N	\N	f
420	auth_user_1766820950	$2b$12$DzmZPlw5XHjuBrfKlIsT1eWWJ1uSXRzOvzSDPyXbWkEfhoNYJ43Tq	auth_user_1766820950@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-27 16:35:50.964039	\N	\N	\N	f
421	regular_user_1766820951	$2b$12$cx6ft.ipVZRHZR5irFcyXu0e4YF/ek8Yhw89ynL1HdoOklpGFn5py	regular_1766820951@example.com	Regular User	Testing	\N	\N	user	t	2025-12-27 16:35:51.623418	\N	\N	\N	f
422	admin_user_1766820951	$2b$12$VDISRHmo0CxqzirhXQP3QuayMaHU3u2j1/yYHjiI.L83PfeoQxFxa	admin_1766820951@example.com	Admin User	IT	\N	\N	admin	t	2025-12-27 16:35:51.818389	\N	\N	\N	f
423	activation_test_1766820951	$2b$12$l.rN1o.gHAflSnbRB03d3O0dV5McHmk6icJFl0SbvTnEpc6RUdxJS	activation_1766820951@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-27 16:35:52.095663	\N	\N	\N	f
424	dept_user_1766820952_0	$2b$12$9sVlCanZq5kND1KOMub9wuPvnw.tJmxn7hX/reslLUhtZJ/c98GSi	dept_user_1766820952_0@example.com	Dept User 0	TestDept_1766820952	\N	\N	user	t	2025-12-27 16:35:51.060047	\N	\N	\N	f
425	dept_user_1766820952_1	$2b$12$83slz7C.HK.EJFsvI0JqzeoOMAtELrQ.NrRVX0OK9GRjAqvPq0YkO	dept_user_1766820952_1@example.com	Dept User 1	TestDept_1766820952	\N	\N	user	t	2025-12-27 16:35:51.255536	\N	\N	\N	f
426	dept_user_1766820952_2	$2b$12$6QVa0q1l4xwOCtl4j.pcb.1cUk8otAi0NrCnOh0YycCN32Trw.xnW	dept_user_1766820952_2@example.com	Dept User 2	TestDept_1766820952	\N	\N	user	t	2025-12-27 16:35:51.450837	\N	\N	\N	f
427	unique_test_1766820951	$2b$12$.WXomnBJPIGWg1Lx6hKTWOkzTyoxINGsY06scA3npYP2FDJb0hjWa	unique_1766820951@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-27 16:35:51.697159	\N	\N	\N	f
443	loginuser_5828a2b9	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:55.332219	\N	2025-12-27 16:35:55.358969	\N	f
444	createsession_89978d33	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:55.410458	\N	2025-12-27 16:35:55.437583	\N	f
445	plaintext_test_fca5a1ba	$2b$12$5PRZ3quvo/8Z3lNv33bS3e4v63ymc11WcPv/2WQgs6F2H7fV75DbG	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:55.685978	\N	\N	\N	f
446	user1_6f4f238c	$2b$12$LInWKfxfaQNpBbAcAEtgaORThBzlYNtVHE/EQOeSwybW63jsoaSsm	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:56.14381	\N	\N	\N	f
447	user2_6f4f238c	$2b$12$LAe.q.iKx6J2OhqD4hXCa.iQlRRJz4tbsgoS3g0RVehdiWz2mfnvS	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:56.143812	\N	\N	\N	f
448	user_user_1d0d87f6	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:56.595595	\N	\N	\N	f
449	admin_user_1d0d87f6	hash	\N	\N	\N	\N	\N	admin	t	2025-12-27 16:35:56.595597	\N	\N	\N	f
450	superadmin_user_1d0d87f6	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-27 16:35:56.595598	\N	\N	\N	f
451	norole_cbca4018	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:56.707538	\N	\N	\N	f
452	mixed_41181bd4_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-27 16:35:56.965775	\N	\N	\N	f
453	mixed_41181bd4_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-27 16:35:56.965778	\N	\N	\N	f
454	mixed_41181bd4_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:56.965779	\N	\N	\N	f
455	mixed_41181bd4_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:56.965779	\N	\N	\N	f
456	mixed_41181bd4_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-27 16:35:56.96578	\N	\N	\N	f
457	auth_user_1766878322	$2b$12$UdzBME6EBZ1kwcY6pJTsVel5G3Py1Eekhv5quwr0fVxTob1HhuveO	auth_user_1766878322@example.com	Auth Test User	Testing	\N	\N	user	t	2025-12-28 08:32:02.208136	\N	\N	\N	f
461	dept_user_1766878323_0	$2b$12$6sWMaluaT1FEtSn8rgp2guUyzPScNiaeop3ZA2G7aWSfdDSHoJvaG	dept_user_1766878323_0@example.com	Dept User 0	TestDept_1766878323	\N	\N	user	t	2025-12-28 08:32:03.797502	\N	\N	\N	f
458	regular_user_1766878322	$2b$12$BHAFTsdVLYJZ8IwvQs58pOOWpztXPta49DJlgVlPRct3kPCNexeWq	regular_1766878322@example.com	Regular User	Testing	\N	\N	user	t	2025-12-28 08:32:02.906609	\N	\N	\N	f
459	admin_user_1766878322	$2b$12$N9RjcKgkR9pkuJZwQRrWve1tDe5EXvZ0AxRntHoWJuzp9IpGVbw2y	admin_1766878322@example.com	Admin User	IT	\N	\N	admin	t	2025-12-28 08:32:03.11166	\N	\N	\N	f
460	activation_test_1766878323	$2b$12$9CrMpyomJmHWkifOWXuFh.0584WgQSWKlPdL42H7n75iy.aqW3n2K	activation_1766878323@example.com	Activation Test	Testing	\N	\N	user	t	2025-12-28 08:32:03.414235	\N	\N	\N	f
462	dept_user_1766878323_1	$2b$12$NaCOSB1U/nTf1fW8vrgo8ufCOS3qxmbK0.3rG7ZYgluBtuEXKNTlS	dept_user_1766878323_1@example.com	Dept User 1	TestDept_1766878323	\N	\N	user	t	2025-12-28 08:32:04.003882	\N	\N	\N	f
463	dept_user_1766878323_2	$2b$12$0xSPgCILxDWMCKeXWCTHheSSdcScs2FzD143C4LgsRRfxVRODDFPq	dept_user_1766878323_2@example.com	Dept User 2	TestDept_1766878323	\N	\N	user	t	2025-12-28 08:32:04.209355	\N	\N	\N	f
464	unique_test_1766878324	$2b$12$GVPF7/OG4BJXPJ467swK6.vkaiWeF7JgYkV5ridWmx447rFQJPk1O	unique_1766878324@example.com	Unique Test 1	Testing	\N	\N	user	t	2025-12-28 08:32:04.479767	\N	\N	\N	f
465	login_test_1766878324	$2b$12$zFykLqXueLRchVlmKegTcOs1Fw10UNoJ6YJkWIxKGmeLNPOCbasYG	login_test_1766878324@example.com	Login Test	Testing	\N	\N	user	t	2025-12-28 08:32:04.76828	\N	2025-12-28 08:32:04.846552	\N	f
466	test_async_1766878324	$2b$12$x6TuL2CD0O50.qF6A9RVxOWCwZLWxGHD1IVlRhnPxNmQ/oiMUHN8y	test_async_1766878324@example.com	Async Test User	Testing	\N	\N	user	t	2025-12-28 08:32:05.167794	\N	\N	\N	f
467	auth_test_1766878325	$2b$12$WGt7yfemqNIoiZ5gMGMQ5OomktDWmAmMA5vORk/QWe5SK/ZOa/Yse	auth_test_1766878325@example.com	Auth Test	Testing	\N	\N	user	t	2025-12-28 08:32:05.446008	\N	\N	\N	f
468	log_test_1766878325	$2b$12$LiIQ4V0Si7o8cKUOxJcO4u3iVktHPJvKp5AhsP/SFp5oO/gIMxgme	log_test_1766878325@example.com	Log Test User	Testing	\N	\N	user	t	2025-12-28 08:32:05.724552	\N	\N	\N	f
469	session_test_1766878326	$2b$12$aAT5D.86AkYzb/2E1iMb0ejA1S32n04Vnzsg2.FTlwDCWxcfceJbq	session_test_1766878326@example.com	Session Test User	Testing	\N	\N	user	t	2025-12-28 08:32:06.274316	\N	\N	\N	f
470	session_update_1766878326	$2b$12$wmJUU7WafB5TH/cbi6AH3ezTwjfRUhToCS4KNbgVrTDFHZlYJW5y2	session_update_1766878326@example.com	Session Update Test	Testing	\N	\N	user	t	2025-12-28 08:32:06.634672	\N	\N	\N	f
471	session_filter_1766878326	$2b$12$k/mXZSEBW7nNrwOplZPjgOTNcSNjKA732Ie8Cmjqpmd27fe3ajh0.	session_filter_1766878326@example.com	Session Filter Test	Testing	\N	\N	user	t	2025-12-28 08:32:07.056075	\N	\N	\N	f
472	hashtest_8f23904d	$2b$12$//VJtI/ruwnOUBSdN9zbVe8gfF7K6gQAPy2.nxz./NH5tNYOMj6Em	hash_8f23904d@test.com	\N	\N	\N	\N	user	t	2025-12-28 08:32:07.397854	\N	\N	\N	f
473	admin_test_2091026f	admin_hash	admin_2091026f@test.com	\N	\N	\N	\N	admin	t	2025-12-28 08:32:04.934817	\N	\N	\N	f
474	deactivate_852eae07	hash	\N	\N	\N	\N	\N	user	f	2025-12-28 08:32:05.017627	\N	\N	\N	f
475	sessiontest_de458697	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:05.114962	\N	\N	\N	f
476	multisession_ab2c201d	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:05.19735	\N	\N	\N	f
477	endsession_365466d9	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:05.28815	\N	\N	\N	f
478	activity_095ce308	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:05.402506	\N	\N	\N	f
479	findactive_47a63ca7	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:05.620494	\N	\N	\N	f
480	loginuser_0e69e5da	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:05.704049	\N	2025-12-28 08:32:05.726746	\N	f
481	createsession_8fb19523	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:05.794577	\N	2025-12-28 08:32:05.817241	\N	f
482	plaintext_test_abd5dc35	$2b$12$ZS9ebyxI6yUZ5xmMPUjH6eaU6Nrb7pfy7DF.fYEfsq/OLpgaDKwHS	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:06.080598	\N	\N	\N	f
483	user1_fbc3035a	$2b$12$eRLfwfQlZuyESISJ2qFIMeeFxTPFgG4t2caQtj78P8UIrzsevFaAW	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:06.563615	\N	\N	\N	f
484	user2_fbc3035a	$2b$12$ZimE7b42GxZ9AZ14WwMlrO1N9FhC/MIWTXeponWq5HxVLdcm21H/y	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:06.563618	\N	\N	\N	f
485	user_user_21b37e1a	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:07.038785	\N	\N	\N	f
486	admin_user_21b37e1a	hash	\N	\N	\N	\N	\N	admin	t	2025-12-28 08:32:07.038789	\N	\N	\N	f
487	superadmin_user_21b37e1a	hash	\N	\N	\N	\N	\N	superadmin	t	2025-12-28 08:32:07.03879	\N	\N	\N	f
488	norole_cfce883d	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:07.119074	\N	\N	\N	f
489	mixed_af4d812e_0	hash	\N	\N	\N	\N	\N	admin	t	2025-12-28 08:32:07.180544	\N	\N	\N	f
490	mixed_af4d812e_1	hash	\N	\N	\N	\N	\N	admin	t	2025-12-28 08:32:07.180548	\N	\N	\N	f
491	mixed_af4d812e_2	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:07.180548	\N	\N	\N	f
492	mixed_af4d812e_3	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:07.180549	\N	\N	\N	f
493	mixed_af4d812e_4	hash	\N	\N	\N	\N	\N	user	t	2025-12-28 08:32:07.180549	\N	\N	\N	f
494	inlinetest	$2b$12$V8n00J2LBAmMRRHiaaUBQeQdt.isRwI3BOKoY.Lb56BTkwfu1haKy	inlinetest@test.com	\N	\N	\N	\N	admin	t	2025-12-29 00:22:29.537804	\N	2025-12-28 15:38:09.451074	\N	\N
495	testuser2	$2b$12$2fm7A/D/ESw/ThmBrdb7XuES2R08kHzy0IPsvwTP3Tn0fQRhL/pz2	testuser2@test.com	Test User 2	\N	\N	\N	user	t	2026-01-03 03:43:15.444483	\N	2026-03-16 17:54:35.942257	\N	f
496	OFFLINE	OFFLINE_MODE_NO_PASSWORD	offline@localhost	Offline User	\N	\N	\N	user	t	2026-01-04 10:58:28.751527	\N	\N	\N	f
512	log_test_1768190654	$2b$12$wiTjLEoZFqdhgjy6VjeSbOayVVJC3vJnkWuhGFnOM.wyAKR3DqzsO	log_test_1768190654@example.com	Log Test User	Testing	\N	\N	user	t	2026-01-12 13:04:14.855898	\N	\N	\N	f
513	session_test_1768190655	$2b$12$nxdwfGoBOWek8.yHb/x2BezIxb/hDCAOOXNAvOwaAjZkdlvxYqC8O	session_test_1768190655@example.com	Session Test User	Testing	\N	\N	user	t	2026-01-12 13:04:15.194329	\N	\N	\N	f
514	session_update_1768190655	$2b$12$Z3Mxw1X98BUyD6G3fosrQeha6N626YFjlbSyqSBr1YRfaH7qCot3C	session_update_1768190655@example.com	Session Update Test	Testing	\N	\N	user	t	2026-01-12 13:04:15.563797	\N	\N	\N	f
515	session_filter_1768190655	$2b$12$uoI2BP4ouD/XjoxTypk9COGp0FUn22kMyvV84PS3jAoLULBeWsceS	session_filter_1768190655@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-01-12 13:04:15.968221	\N	\N	\N	f
516	hashtest_ac0b979f	$2b$12$d3UkyeZ4.x4y0SW0FcnSceCJLMYTJEz8006F2eXr3nsOiNxMH62RS	hash_ac0b979f@test.com	\N	\N	\N	\N	user	t	2026-01-12 13:04:16.29629	\N	\N	\N	f
517	admin_test_291ffda2	admin_hash	admin_291ffda2@test.com	\N	\N	\N	\N	admin	t	2026-01-12 13:04:16.534282	\N	\N	\N	f
518	deactivate_c50085db	hash	\N	\N	\N	\N	\N	user	f	2026-01-12 13:04:16.633097	\N	\N	\N	f
519	sessiontest_4270b3c3	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:16.7252	\N	\N	\N	f
498	test_profile_222982	$2b$12$9GBX7GiK93pi.r3NgC5hJOg6rA74B7XSQNjEePYJmbmL2Q1FwPcmC	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-01-12 13:03:13.730386	2	\N	\N	f
520	multisession_efc8d37a	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:16.812368	\N	\N	\N	f
499	test_created_222982	$2b$12$ZqiKpfw9WQ.AqtUsIWmnNuZ58cCVyLFyhrrpQetQjGM9S7CZg6.LG	\N	\N	\N	\N	\N	user	f	2026-01-12 13:03:14.212632	2	\N	\N	f
521	endsession_554275a2	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:16.900872	\N	\N	\N	f
522	activity_ea339a44	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:17.101693	\N	\N	\N	f
523	findactive_f97ebc07	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:17.313141	\N	\N	\N	f
524	loginuser_b111fd4f	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:17.39638	\N	2026-01-12 13:04:17.420117	\N	f
500	test_fullprof_222982	$2b$12$1kJJpsGdkauHCO8s2ZrxlONSCcOcEo/X7Iuop243B6edXbahE/HZS	test_222982@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-01-12 13:03:17.978086	2	\N	\N	f
525	createsession_df69fc34	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:17.477832	\N	2026-01-12 13:04:17.503877	\N	f
526	plaintext_test_af2e7ed2	$2b$12$LqqvupK614zoQbSG3sm4SOL5fyEdnnkmZIyk8yjV1awPGN3Z.PSEy	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:17.761348	\N	\N	\N	f
527	user1_89013c3a	$2b$12$UyjqiBYmRwV2.TYvGTkgm.MkX5o6LevTcxBDi2ou6MYUf8aZCJxFe	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:18.19935	\N	\N	\N	f
501	auth_user_1768190651	$2b$12$q9rf9ViORCsp5YAGX9RfVuDyKQB47u8IpkXfNFUcn8iTW0WBhHyYG	auth_user_1768190651@example.com	Auth Test User	Testing	\N	\N	user	t	2026-01-12 13:04:11.624131	\N	\N	\N	f
502	regular_user_1768190652	$2b$12$78FYpfJ8qSqHEKsCIkHP1ul1YfbfLtMawfy/ALQKdjNofUe2wqFYW	regular_1768190652@example.com	Regular User	Testing	\N	\N	user	t	2026-01-12 13:04:12.27067	\N	\N	\N	f
503	admin_user_1768190652	$2b$12$nVF1wyUqQj/LSsteHsychOvQOttMlEY1t6tJlc9.I.HFlH464bgzO	admin_1768190652@example.com	Admin User	IT	\N	\N	admin	t	2026-01-12 13:04:12.454937	\N	\N	\N	f
528	user2_89013c3a	$2b$12$fLaHnn99GGzaLIs2Oo8Cr.yYOmFxSa5YXm2bW8mC.lt0ek74xE8Li	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:18.199354	\N	\N	\N	f
504	activation_test_1768190652	$2b$12$1AqcRhmQHvT6wAQekQxxp.4ijAfKsFghlvdhbr42isaEsPbUGsctW	activation_1768190652@example.com	Activation Test	Testing	\N	\N	user	t	2026-01-12 13:04:12.729479	\N	\N	\N	f
505	dept_user_1768190652_0	$2b$12$5xIMJgZ0Xv9fTmkraSWLieocuaDRSK0fpkK6.Rk3u5hci.9ihjj3G	dept_user_1768190652_0@example.com	Dept User 0	TestDept_1768190652	\N	\N	user	t	2026-01-12 13:04:13.104383	\N	\N	\N	f
506	dept_user_1768190652_1	$2b$12$i/kXDrJlsL6XDvnGYNbty.oh.ZwetJxyY4cOYs2RtPYO6UTKWlsVK	dept_user_1768190652_1@example.com	Dept User 1	TestDept_1768190652	\N	\N	user	t	2026-01-12 13:04:13.287683	\N	\N	\N	f
507	dept_user_1768190652_2	$2b$12$gDvm4MXlqsRj1wJGX8NCj.NjYHztFGGnwwFgiwnz9Y52rKHl4Z.ju	dept_user_1768190652_2@example.com	Dept User 2	TestDept_1768190652	\N	\N	user	t	2026-01-12 13:04:13.473052	\N	\N	\N	f
508	unique_test_1768190653	$2b$12$tuIgMsK2625TWs4KYvnFqOZuMe87LipUZkpxOwEAvQ8nnw/eRt9fO	unique_1768190653@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-01-12 13:04:13.696097	\N	\N	\N	f
509	login_test_1768190653	$2b$12$BA3679PKew3ChOS4OCtMte6/ewHBtXeLjOx15iFW/N2T846zEmzhq	login_test_1768190653@example.com	Login Test	Testing	\N	\N	user	t	2026-01-12 13:04:13.97383	\N	2026-01-12 13:04:14.046962	\N	f
510	test_async_1768190654	$2b$12$IToPIMXlHXtHUbpmtFiaCuEN5umQylHc1nDbGL3yMn7cdFY0WSuMy	test_async_1768190654@example.com	Async Test User	Testing	\N	\N	user	t	2026-01-12 13:04:14.316825	\N	\N	\N	f
529	user_user_57a6137b	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:18.631638	\N	\N	\N	f
511	auth_test_1768190654	$2b$12$fOEdT2xJIjSjHORHmEpw8.KNz6J/cbPIrZw7ObCQWYBISNrPfq8ce	auth_test_1768190654@example.com	Auth Test	Testing	\N	\N	user	t	2026-01-12 13:04:14.578926	\N	\N	\N	f
530	admin_user_57a6137b	hash	\N	\N	\N	\N	\N	admin	t	2026-01-12 13:04:18.631641	\N	\N	\N	f
531	superadmin_user_57a6137b	hash	\N	\N	\N	\N	\N	superadmin	t	2026-01-12 13:04:18.631643	\N	\N	\N	f
532	norole_2967aae3	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:18.69654	\N	\N	\N	f
533	mixed_62aab765_0	hash	\N	\N	\N	\N	\N	admin	t	2026-01-12 13:04:18.758937	\N	\N	\N	f
534	mixed_62aab765_1	hash	\N	\N	\N	\N	\N	admin	t	2026-01-12 13:04:18.75894	\N	\N	\N	f
535	mixed_62aab765_2	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:18.758942	\N	\N	\N	f
536	mixed_62aab765_3	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:18.758943	\N	\N	\N	f
537	mixed_62aab765_4	hash	\N	\N	\N	\N	\N	user	t	2026-01-12 13:04:18.758945	\N	\N	\N	f
538	auth_user_1768288981	$2b$12$kEf3vwcF0nQQa6VACHpKSeCkh3jWOB.mmx1QJiFvkkRMp6VT2.gHS	auth_user_1768288981@example.com	Auth Test User	Testing	\N	\N	user	t	2026-01-13 16:23:01.409178	\N	\N	\N	f
539	regular_user_1768288979	$2b$12$I9Wca5Xih2MMokjy5rk2Su.eCnVXN38rcFR1Il2n/uQizixCnQ7KK	regular_1768288979@example.com	Regular User	Testing	\N	\N	user	t	2026-01-13 16:22:59.269533	\N	\N	\N	f
540	admin_user_1768288979	$2b$12$hn3kGteKBDIJng3fOugiVuE.bpGKbJJJ4KMq.Mv639bSv4O470RUq	admin_1768288979@example.com	Admin User	IT	\N	\N	admin	t	2026-01-13 16:22:59.472839	\N	\N	\N	f
545	unique_test_1768288980	$2b$12$5IHfe5zljG9RKauZ85F79ugzNMHD8fio19PaEKfSWDRDN8DjbJ4WK	unique_1768288980@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-01-13 16:23:00.807904	\N	\N	\N	f
541	activation_test_1768288979	$2b$12$71afiBBaein7hrs0I6g4.un1rDR/sr.F96XYB8tMMXNT5CRHfUUrS	activation_1768288979@example.com	Activation Test	Testing	\N	\N	user	t	2026-01-13 16:22:59.762826	\N	\N	\N	f
542	dept_user_1768288979_0	$2b$12$LtWQRrL31aDnzwb6KtlsguB2M0yet./0m.fkQdRIht9X2pePHAy7.	dept_user_1768288979_0@example.com	Dept User 0	TestDept_1768288979	\N	\N	user	t	2026-01-13 16:23:00.158051	\N	\N	\N	f
543	dept_user_1768288979_1	$2b$12$iQQbOQjU2hDaQ38EMrSwrexc.6WIrUdCdaYK6lYttIrRBQuTtMWUm	dept_user_1768288979_1@example.com	Dept User 1	TestDept_1768288979	\N	\N	user	t	2026-01-13 16:23:00.362215	\N	\N	\N	f
544	dept_user_1768288979_2	$2b$12$bnKaXtwr.0ycoYX7X3z2MO5qzqC1qJx9C2k4Xz99z6r.y8RiUQfs6	dept_user_1768288979_2@example.com	Dept User 2	TestDept_1768288979	\N	\N	user	t	2026-01-13 16:23:00.560838	\N	\N	\N	f
546	login_test_1768288980	$2b$12$il5Zatjdu.JCmYfx0ylgAefH8yEKSmKVSpMPW759vGUAUyEkbGl3S	login_test_1768288980@example.com	Login Test	Testing	\N	\N	user	t	2026-01-13 16:23:01.08897	\N	2026-01-13 16:23:01.165502	\N	f
547	test_async_1768288981	$2b$12$bhim0kGt0Ag2BW47wO5eJuU4vysJB2P.pZl/jpAeAVG/l1GlzskxG	test_async_1768288981@example.com	Async Test User	Testing	\N	\N	user	t	2026-01-13 16:23:01.481411	\N	\N	\N	f
548	auth_test_1768288981	$2b$12$zI0JWcM5HxIg2QQyn6tgfu73CV.Z7Wo8DPt8npkpKzkfWAxVOSKLy	auth_test_1768288981@example.com	Auth Test	Testing	\N	\N	user	t	2026-01-13 16:23:01.81401	\N	\N	\N	f
549	log_test_1768288981	$2b$12$DevEN2ZWd8JV9lsfYzfZp.44Z2htv9V9Cp07Jm19Q955t16QQW3NK	log_test_1768288981@example.com	Log Test User	Testing	\N	\N	user	t	2026-01-13 16:23:02.102582	\N	\N	\N	f
550	session_test_1768288982	$2b$12$FlUoWKt0A7rxOawsUYaleeHN.IJZJ7R/ApsLur5Nki/N4/2C0LwGq	session_test_1768288982@example.com	Session Test User	Testing	\N	\N	user	t	2026-01-13 16:23:02.676054	\N	\N	\N	f
551	session_update_1768288982	$2b$12$z2T1.WG9euEL8lEe0fpLbeIh/CZ2Y4Bxf5p87STkVRV5i4yj7XrL.	session_update_1768288982@example.com	Session Update Test	Testing	\N	\N	user	t	2026-01-13 16:23:03.043952	\N	\N	\N	f
552	session_filter_1768288983	$2b$12$gQHj1rFPgcnmLVslUwN/Z.jT1NPY3KwfNhjolH1e3Rt2Ns6Dk2jWC	session_filter_1768288983@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-01-13 16:23:03.468806	\N	\N	\N	f
553	hashtest_5d5b9a93	$2b$12$AhFLQ.i98I4aDNz3PhTLa.2dfSV8Iyo69QzoV7M3zvffTZ9HEEmKW	hash_5d5b9a93@test.com	\N	\N	\N	\N	user	t	2026-01-13 16:23:03.827966	\N	\N	\N	f
554	admin_test_324a1394	admin_hash	admin_324a1394@test.com	\N	\N	\N	\N	admin	t	2026-01-13 16:23:04.11484	\N	\N	\N	f
555	deactivate_c8edc3b6	hash	\N	\N	\N	\N	\N	user	f	2026-01-13 16:23:04.170335	\N	\N	\N	f
556	sessiontest_b96820a6	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:04.332176	\N	\N	\N	f
557	multisession_2039cdf5	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:04.429681	\N	\N	\N	f
558	endsession_333e944c	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:04.521692	\N	\N	\N	f
559	activity_affde55e	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:04.634451	\N	\N	\N	f
560	findactive_a7cc1195	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:04.863085	\N	\N	\N	f
561	loginuser_2c4014c7	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:04.954591	\N	2026-01-13 16:23:04.980333	\N	f
562	createsession_d13a9f77	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:05.042814	\N	2026-01-13 16:23:05.071111	\N	f
563	plaintext_test_414214a0	$2b$12$9CdqeKLhVZmo2l1cr.AYHOHH28ZP5tWOVTASHwpqoowelM3114CtS	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:05.337138	\N	\N	\N	f
564	user1_1a3d7e1a	$2b$12$Gnqhb67ILR8zFGBHC/bOmeLkO7S6v7N5yY5ENcNvZ35kNTz5o1Iba	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:05.814272	\N	\N	\N	f
565	user2_1a3d7e1a	$2b$12$MoCIScNajZDFx8IaUckLZeHEtQpYnclP3yQnMlwQDHKzCfpEXTUya	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:05.814277	\N	\N	\N	f
566	user_user_b2a89b1f	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:06.290321	\N	\N	\N	f
567	admin_user_b2a89b1f	hash	\N	\N	\N	\N	\N	admin	t	2026-01-13 16:23:06.290325	\N	\N	\N	f
568	superadmin_user_b2a89b1f	hash	\N	\N	\N	\N	\N	superadmin	t	2026-01-13 16:23:06.290327	\N	\N	\N	f
569	norole_244b22bb	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:06.359309	\N	\N	\N	f
570	mixed_a78222a9_0	hash	\N	\N	\N	\N	\N	admin	t	2026-01-13 16:23:06.42093	\N	\N	\N	f
571	mixed_a78222a9_1	hash	\N	\N	\N	\N	\N	admin	t	2026-01-13 16:23:06.420934	\N	\N	\N	f
572	mixed_a78222a9_2	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:06.420935	\N	\N	\N	f
573	mixed_a78222a9_3	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:06.420937	\N	\N	\N	f
574	mixed_a78222a9_4	hash	\N	\N	\N	\N	\N	user	t	2026-01-13 16:23:06.420938	\N	\N	\N	f
585	auth_test_1768331607	$2b$12$6SDP7bsKoPw9fqSkwWJ3eOivs2i89RheuBNiVc.Lf7VfYhunzh4xa	auth_test_1768331607@example.com	Auth Test	Testing	\N	\N	user	t	2026-01-14 04:13:27.871263	\N	\N	\N	f
586	log_test_1768331607	$2b$12$HBg9YANYS3j5ZVciRBbaOewxofmp6YgiSaPx.lGeWaNwCJaJpx.Ae	log_test_1768331607@example.com	Log Test User	Testing	\N	\N	user	t	2026-01-14 04:13:28.133798	\N	\N	\N	f
587	session_test_1768331608	$2b$12$.BQN3XED0QIABllHKzWGfO4QYP/hJJMsr7x3OOLn.HFBBNBuuvG1m	session_test_1768331608@example.com	Session Test User	Testing	\N	\N	user	t	2026-01-14 04:13:28.501066	\N	\N	\N	f
588	session_update_1768331608	$2b$12$uYNxeUlsF9hzJB7kRsXFauOyVOS8IV9JsrWr2MBQHMst3mJrOQIc6	session_update_1768331608@example.com	Session Update Test	Testing	\N	\N	user	t	2026-01-14 04:13:28.910687	\N	\N	\N	f
589	session_filter_1768331609	$2b$12$nDs0gvLu1rmBSBEZp7BNTuTlh5IIUa3ETroSJzN91ZYlx3c0lfTUW	session_filter_1768331609@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-01-14 04:13:29.272221	\N	\N	\N	f
590	hashtest_b2fd18d1	$2b$12$EPztd83YWi3zJPhltDz97eqqpZtojd3.0d8z7a/bBoVUrZYYgUtGi	hash_b2fd18d1@test.com	\N	\N	\N	\N	user	t	2026-01-14 04:13:29.602627	\N	\N	\N	f
591	admin_test_00bfdee8	admin_hash	admin_00bfdee8@test.com	\N	\N	\N	\N	admin	t	2026-01-14 04:13:29.850314	\N	\N	\N	f
592	deactivate_906d9197	hash	\N	\N	\N	\N	\N	user	f	2026-01-14 04:13:29.911609	\N	\N	\N	f
593	sessiontest_9e60a238	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:29.997622	\N	\N	\N	f
594	multisession_47142c7c	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:30.080807	\N	\N	\N	f
595	endsession_4fc05931	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:30.165764	\N	\N	\N	f
596	activity_9a69d5fd	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:30.276797	\N	\N	\N	f
597	findactive_fffa6754	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:30.496275	\N	\N	\N	f
598	loginuser_05734e01	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:30.589076	\N	2026-01-14 04:13:30.609825	\N	f
599	createsession_b12991b5	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:30.669942	\N	2026-01-14 04:13:30.692151	\N	f
600	plaintext_test_278e30f3	$2b$12$aTKRYE6oQLMXErtmY3K3keVfbHuKn4sNgh8vwtLyFhB5.Ft1uPine	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:30.931784	\N	\N	\N	f
601	user1_0034513a	$2b$12$p2hSNo.0aPYP.mNVN7vuBePvsoA9.MgxvLEqzCSaXD7yLSeoC4rVe	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:31.361676	\N	\N	\N	f
602	user2_0034513a	$2b$12$x3SuBEsr6wtSyjnYhA0fCugmVhL1HoaODqYhuYPWUeJiQgj5Cg6GK	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:31.36168	\N	\N	\N	f
603	user_user_5bf04d22	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:31.807582	\N	\N	\N	f
604	admin_user_5bf04d22	hash	\N	\N	\N	\N	\N	admin	t	2026-01-14 04:13:31.807585	\N	\N	\N	f
575	auth_user_1768331604	$2b$12$Gkp/f41dmd6e9RrTJXY6qecomXyn1nUGZhlZeQobUsic3B/sjIL9C	auth_user_1768331604@example.com	Auth Test User	Testing	\N	\N	user	t	2026-01-14 04:13:24.735428	\N	\N	\N	f
576	regular_user_1768331605	$2b$12$LgAviu72xNdEesLWx0riReIpf/OdVsv15oqhDBzVleDCxsj8.ZanS	regular_1768331605@example.com	Regular User	Testing	\N	\N	user	t	2026-01-14 04:13:25.368927	\N	\N	\N	f
577	admin_user_1768331605	$2b$12$TVQNZMY2FqegxOybnU1o7e0md9.UapVEc00DsgXUDIu0HM/2h5Uny	admin_1768331605@example.com	Admin User	IT	\N	\N	admin	t	2026-01-14 04:13:25.552352	\N	\N	\N	f
605	superadmin_user_5bf04d22	hash	\N	\N	\N	\N	\N	superadmin	t	2026-01-14 04:13:31.807587	\N	\N	\N	f
578	activation_test_1768331605	$2b$12$99Tt0fVD0Dy8MgW0qrW2FeUz1wolcZ8TYGay97/Ul5dGdBYYhoP7y	activation_1768331605@example.com	Activation Test	Testing	\N	\N	user	t	2026-01-14 04:13:25.827488	\N	\N	\N	f
579	dept_user_1768331606_0	$2b$12$Ttpsn50TvRYvVLysSx5/zubdabhC1xLvhBYq2SwyPTJG0xxhrjU8e	dept_user_1768331606_0@example.com	Dept User 0	TestDept_1768331606	\N	\N	user	t	2026-01-14 04:13:26.193137	\N	\N	\N	f
580	dept_user_1768331606_1	$2b$12$RXBA1QxJf.WdwtSaA/IzFOFMy8XRg9YLpYE3TB0SxE3uN6OoHz5Yu	dept_user_1768331606_1@example.com	Dept User 1	TestDept_1768331606	\N	\N	user	t	2026-01-14 04:13:26.377032	\N	\N	\N	f
581	dept_user_1768331606_2	$2b$12$.Di3lBCTtUoZBDTu/t/PkubHOruFXjh8b5Y4HmApXgTKmonhCKMFq	dept_user_1768331606_2@example.com	Dept User 2	TestDept_1768331606	\N	\N	user	t	2026-01-14 04:13:26.56083	\N	\N	\N	f
582	unique_test_1768331606	$2b$12$uUYDnk30kpbzznZ0HKvUE.t7ZC3QZjwU3PppvB9LyFYaxInkQoism	unique_1768331606@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-01-14 04:13:26.785483	\N	\N	\N	f
583	login_test_1768331607	$2b$12$1WpOLhXas2wSDegbLRJ5Oub5Pp4v4hKlxl6oqgtgL9qCDbnIUkHm.	login_test_1768331607@example.com	Login Test	Testing	\N	\N	user	t	2026-01-14 04:13:27.205963	\N	2026-01-14 04:13:27.294799	\N	f
584	test_async_1768331607	$2b$12$pFoUupkkl1UUK5vz4H8FOeJXFtD1cKx3l9vPeArtGW.6AUhHE/eVe	test_async_1768331607@example.com	Async Test User	Testing	\N	\N	user	t	2026-01-14 04:13:27.607842	\N	\N	\N	f
606	norole_7facf445	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:31.875426	\N	\N	\N	f
607	mixed_bca50310_0	hash	\N	\N	\N	\N	\N	admin	t	2026-01-14 04:13:31.937525	\N	\N	\N	f
608	mixed_bca50310_1	hash	\N	\N	\N	\N	\N	admin	t	2026-01-14 04:13:31.937529	\N	\N	\N	f
609	mixed_bca50310_2	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:31.937531	\N	\N	\N	f
610	mixed_bca50310_3	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:31.937532	\N	\N	\N	f
611	mixed_bca50310_4	hash	\N	\N	\N	\N	\N	user	t	2026-01-14 04:13:31.937533	\N	\N	\N	f
615	test_profile_368999	$2b$12$.NuyfZAx.bFHzDXwW.2rPema1kJzs7njsTvC4Rq7tJbgw1sQ4aT6u	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-01-14 05:37:04.903088	2	\N	\N	f
612	test_profile_363894	$2b$12$ah5hM6AJHIPmqPi1vExM3OR0Ulmeh2oNxQGS53GMQWPDWvUHJYYFe	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-01-14 04:13:53.997205	2	\N	\N	f
613	test_created_363894	$2b$12$a3Dw8fsQbwJfon9/X6RAhOwCgnlzMi4yEp9rpcfFCR5o8BwgqFvle	\N	\N	\N	\N	\N	user	f	2026-01-14 04:13:54.488821	2	\N	\N	f
616	test_created_368999	$2b$12$jHksCFoaHoWGeHFPIaf2kuu.bI3I8FZhx4vlA3WQ3j5BO7jvsBwrC	\N	\N	\N	\N	\N	user	f	2026-01-14 05:37:05.455721	2	\N	\N	f
614	test_fullprof_363894	$2b$12$mWtbBGhvjtysJalZxRU7pOTUrLQE150X53RbJlvDuyx1m9jS6i.vK	test_363894@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-01-14 04:13:58.522674	2	\N	\N	f
620	test_fullprof_380802	$2b$12$DhuwKYTdLOHTPP1AUJJN4utUhV4Z6koR8drHWANdgpZfgV6QwmeAK	test_380802@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-01-14 08:54:11.933526	2	\N	\N	f
618	test_profile_380802	$2b$12$p/fKlN.Pw.U4GpWibI9vDuCYFt91W51EEWKwXC/4TpwOfr2F3UpUi	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-01-14 08:54:07.637424	2	\N	\N	f
617	test_fullprof_368999	$2b$12$pdP6j3GCAhIzgroacL8fTuh0yvUlZC8e.YjdBXLpqXNNA0FP36hPe	test_368999@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-01-14 05:37:09.301035	2	\N	\N	f
619	test_created_380802	$2b$12$0HKXKBBr718Qkf6v38aIDOndGMyikPrwNOQTe4dHL17.tolOFNJv2	\N	\N	\N	\N	\N	user	f	2026-01-14 08:54:08.123949	2	\N	\N	f
621	test_profile_380886	$2b$12$c6342qn4qqzORbsgs2PZ6.da1D8Ffbf4PUn1QEP8VM6QCHYQjGFHW	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-01-14 08:55:23.045217	2	\N	\N	f
622	test_created_380886	$2b$12$TUHLDgQrEPcjWtl4DRHzI.cpyM1Z0qGESD/ExnR124U9tJEtlZUpO	\N	\N	\N	\N	\N	user	f	2026-01-14 08:55:23.531056	2	\N	\N	f
623	test_fullprof_380886	$2b$12$x/kq7tVks3SDPgcduqwhpeChJkVyspS2oZ1hCq8KTxM26UOAoJ2SS	test_380886@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-01-14 08:55:27.35708	2	\N	\N	f
624	test_profile_380980	$2b$12$GIU/tPp7KR4Tq/a7PjQuDuxofOgswWhvoqCfZlVELun5EVK7Hj5Dq	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-01-14 08:56:36.168781	2	\N	\N	f
625	test_created_380980	$2b$12$Ytquh3XNQ0hh63PTzHf4geRhBw8f3ZXIcvZmNQGaDpX7hlVIPTCau	\N	\N	\N	\N	\N	user	f	2026-01-14 08:56:36.668251	2	\N	\N	f
626	test_fullprof_380980	$2b$12$QC4PFQZg1u9BSd7Y7a0.guYQrsUmdyRSKeBGkiUWqAV4Z2S8EToeq	test_380980@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-01-14 08:56:40.547291	2	\N	\N	f
638	login_test_1773590926	$2b$12$6c5MwQeD.H4UYlhE79z9w.Mt0EzYuY3ZAV/W9.oMYxzwH3ok.ju1S	login_test_1773590926@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 01:08:46.230209	\N	2026-03-16 01:08:46.298881	\N	f
639	test_async_1773590926	$2b$12$I2JV5khLfSvmEzVJRNzH9uBEWKjB6mspIH2CWCsv582h2PJcVIaxe	test_async_1773590926@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 01:08:46.589041	\N	\N	\N	f
628	test_created_846170	$2b$12$SPV3j8sId1eMJR1svt8BG.Pjtthr5fGkS08JR.VO5yv054spLQNIS	\N	\N	\N	\N	\N	user	f	2026-01-31 07:56:15.517566	2	\N	\N	f
640	auth_test_1773590926	$2b$12$3zmCzqhg6az/HtNl5Z0BhexFI1pT8EoV4wkS/Elez8C7WdDxFUWI2	auth_test_1773590926@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 01:08:46.876791	\N	\N	\N	f
641	log_test_1773590926	$2b$12$qwsYD/D./WNwUCV32F1yHeVg4T9uiVWI1Rf7yAWvIV1PJuTlpFLVm	log_test_1773590926@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 01:08:47.159376	\N	\N	\N	f
642	session_test_1773590927	$2b$12$aQZFXxEnMIS7YJc0qWYnledGGuXTbJrdt6HIqXZ0U.p6s.dr5Jtty	session_test_1773590927@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 01:08:47.537819	\N	\N	\N	f
643	session_update_1773590927	$2b$12$C74F73MXD/XTUA.8KLZL4.6Tm/tKP99K7owQoRWA8PRBgWoITjXYS	session_update_1773590927@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 01:08:47.90381	\N	\N	\N	f
644	session_filter_1773590928	$2b$12$s2tQUYSQHA9ZPF4fSCXkVOamYHM9PbcRccytneY9vYw1IZzY7Ed3O	session_filter_1773590928@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 01:08:48.283172	\N	\N	\N	f
5	test_pw_change	$2b$12$nfH44z0s0Ez1R82xUdyB3Orgatx9JZZJFboqKiZkRTSkKK8fx0zhG	\N	\N	\N	\N	\N	user	t	2025-12-16 05:44:42.123219	2	2026-03-16 03:21:15.43799	2026-03-16 03:21:15.110585	f
645	hashtest_43147292	$2b$12$aP0Rkd4j9KnqHOsOMpuJ/eyHg02VFLfreJ.hCoPsx.bfxZ3KQgUKW	hash_43147292@test.com	\N	\N	\N	\N	user	t	2026-03-16 01:08:48.632993	\N	\N	\N	f
646	admin_test_8c455b96	admin_hash	admin_8c455b96@test.com	\N	\N	\N	\N	admin	t	2026-03-16 01:08:48.886695	\N	\N	\N	f
647	deactivate_a460d44d	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 01:08:48.950284	\N	\N	\N	f
648	sessiontest_1217296a	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:49.030556	\N	\N	\N	f
6	test_must_change	$2b$12$NTxE2yjs40ijOsZYJAzfnu9YQrG9wj/pwUbrivOgLxP.okhYPR21a	\N	\N	\N	\N	\N	user	t	2025-12-16 05:44:44.119912	2	2026-03-16 03:21:17.979276	2026-03-16 03:21:17.698748	f
649	multisession_7822dbc6	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:49.15112	\N	\N	\N	f
629	test_fullprof_846170	$2b$12$smbfh3NpyTsLaPTO2uXDMe1fDQ3HNuFuDZ/ZFU3V9ua7qn/PuUo6u	test_846170@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-01-31 07:56:20.660739	2	\N	\N	f
650	endsession_116814f8	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:49.242286	\N	\N	\N	f
651	activity_98af5ea5	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:49.355212	\N	\N	\N	f
652	findactive_d778e6ab	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:49.576693	\N	\N	\N	f
630	auth_user_1773590923	$2b$12$IgtuqkPcgp6hBRGejDpjaOws6RHPeu2fgtpDhSfTH3pvRsjaPFEdS	auth_user_1773590923@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 01:08:43.286193	\N	\N	\N	f
631	regular_user_1773590923	$2b$12$tfjlWocoThVEhL3ygXghFeDIZDPPQqz3cJNc9ugPTwCIwM8rqyhd6	regular_1773590923@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 01:08:44.003997	\N	\N	\N	f
632	admin_user_1773590923	$2b$12$PWn5Nraj6KCBrMhVc/YKmulSOKXCU08q4uciCcQDM7ndZEtAlz04C	admin_1773590923@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 01:08:44.203371	\N	\N	\N	f
633	activation_test_1773590924	$2b$12$3yR9ml75G5d4MIAHorH9cuCmq5/JjIpLTaX8cFALeRTiafRNowXTq	activation_1773590924@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 01:08:44.536802	\N	\N	\N	f
634	dept_user_1773590924_0	$2b$12$zPKmE6ZTYSAdCesEcaXrtuXxC1Od7ryS8c3pGRSp8zwNIL8GBzKdW	dept_user_1773590924_0@example.com	Dept User 0	TestDept_1773590924	\N	\N	user	t	2026-03-16 01:08:44.93232	\N	\N	\N	f
9	test_reset_pw	$2b$12$Fzg0yUnJ.L7PZ1vYRTJHG.y3MuIWLjqTYeJfM5jeIbR3VMBFzHsh.	\N	\N	\N	\N	\N	user	t	2025-12-16 05:44:46.577504	2	2026-03-16 03:21:19.960678	2026-03-16 03:21:19.673872	t
627	test_profile_846170	$2b$12$YOGCCoSgSAgmcSWnBx36zOB6dM2HWwyZgJwfKgkc.Ry90UVsn7cMW	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-01-31 07:56:14.760621	2	\N	\N	f
635	dept_user_1773590924_1	$2b$12$V6JLRcu7MqoC3U/4l7xfE.dO/DwuLD.lhPeG07qbB1sPNfGwn3aRe	dept_user_1773590924_1@example.com	Dept User 1	TestDept_1773590924	\N	\N	user	t	2026-03-16 01:08:45.1302	\N	\N	\N	f
10	test_deactivate	$2b$12$juyuKLfMEDwxdWhm9.dEMe9azcZ8rvFxe2f3J.vZnxlVSbQT/QBPy	\N	\N	\N	\N	\N	user	f	2025-12-16 05:44:47.4517	2	\N	\N	f
636	dept_user_1773590924_2	$2b$12$IsV1TPSaw1HCecRErQmiYuXN966Lmu7jogqXgjt5YnFtNwPBvYogy	dept_user_1773590924_2@example.com	Dept User 2	TestDept_1773590924	\N	\N	user	t	2026-03-16 01:08:45.329018	\N	\N	\N	f
637	unique_test_1773590925	$2b$12$MrZRxjU5hoNKcPsC00LD4uWYoENtsKJPNxqjaJUw7oHWqFjCXhYU2	unique_1773590925@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 01:08:45.605798	\N	\N	\N	f
653	loginuser_0f1fa27a	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:49.71534	\N	2026-03-16 01:08:49.73995	\N	f
654	createsession_9860cf80	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:49.807221	\N	2026-03-16 01:08:49.838697	\N	f
655	plaintext_test_4f3cf52b	$2b$12$cGF/ekr7FFPnOdIfqsEJd.DAApJq7k2xO3WFEtdzfTCrYU/hFpfIm	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:50.11147	\N	\N	\N	f
656	user1_f2f917a1	$2b$12$mCPcP5yNBV4JaPjwESx5nOmeA2VUzibrkCYZ8ffmNa2YARyE.YUc2	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:50.577077	\N	\N	\N	f
657	user2_f2f917a1	$2b$12$uvlxyGRGh9fKIyk0wt11Q..bMox/GvmZIuufIfn3zTZMqvHNp/mim	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:50.577081	\N	\N	\N	f
658	user_user_77ca018c	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:51.046326	\N	\N	\N	f
659	admin_user_77ca018c	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:08:51.046329	\N	\N	\N	f
660	superadmin_user_77ca018c	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 01:08:51.046331	\N	\N	\N	f
661	norole_f1604645	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:51.185793	\N	\N	\N	f
662	mixed_9e11aa45_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:08:51.255427	\N	\N	\N	f
663	mixed_9e11aa45_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:08:51.25543	\N	\N	\N	f
664	mixed_9e11aa45_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:51.255432	\N	\N	\N	f
665	mixed_9e11aa45_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:51.255433	\N	\N	\N	f
666	mixed_9e11aa45_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:08:51.255435	\N	\N	\N	f
667	auth_user_1773591018	$2b$12$DERHamBztgs/bLuxM2UBROit7EeFj/wZwgIGXBmsaSd8ZvIg2YwdC	auth_user_1773591018@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 01:10:18.705094	\N	\N	\N	f
668	regular_user_1773591019	$2b$12$Z2y/qZzCjI9z8QCah7CH3uiHA8zur9PJS1x5qxdinZTrmnkYG25yu	regular_1773591019@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 01:10:19.382559	\N	\N	\N	f
669	admin_user_1773591019	$2b$12$OvRP2iZoSXSEc57poztxQO21.n0K.LdXerIKPfm49rzbMOspx2EWa	admin_1773591019@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 01:10:19.583829	\N	\N	\N	f
707	activation_test_1773591138	$2b$12$EJRY4aDvs0DvMWYrvqplAe/UfDZH88z7ayVo3ybq5JOoDxv5cKwzy	activation_1773591138@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 01:12:19.187781	\N	\N	\N	f
670	activation_test_1773591019	$2b$12$B9o/AD7y/7S6.kjiU1AbQeIExF3yGTTAnhVXKveybTnJjHdqf3jLe	activation_1773591019@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 01:10:19.864435	\N	\N	\N	f
671	dept_user_1773591020_0	$2b$12$L0GNe6S1pb50PnVeRFwq6.KoP5gEMYd1YHVSpDFq8cNRoEj.1KJVe	dept_user_1773591020_0@example.com	Dept User 0	TestDept_1773591020	\N	\N	user	t	2026-03-16 01:10:20.277061	\N	\N	\N	f
672	dept_user_1773591020_1	$2b$12$7JIsroKLcLCQVDn0.ZZ4L.gwt8DZAIr7GFLs/6jx/zw/apoBmS6tK	dept_user_1773591020_1@example.com	Dept User 1	TestDept_1773591020	\N	\N	user	t	2026-03-16 01:10:20.475346	\N	\N	\N	f
673	dept_user_1773591020_2	$2b$12$MeL8UKCM82f/IRDC8iCNZ.GJaFbHMWNCG11ceVGHy1V6L9OyN7/su	dept_user_1773591020_2@example.com	Dept User 2	TestDept_1773591020	\N	\N	user	t	2026-03-16 01:10:20.675808	\N	\N	\N	f
674	unique_test_1773591020	$2b$12$6FenycJWuipWkFpAM67NK.vNynUhwCB9s9we97tkJ1ocxCjZ9Iety	unique_1773591020@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 01:10:20.907437	\N	\N	\N	f
675	login_test_1773591020	$2b$12$xubTPryek7Q5qNdZrBjjoO8Us1NUJ7SxD00M1YC53EoonGuVVNLK.	login_test_1773591020@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 01:10:21.176304	\N	2026-03-16 01:10:21.245234	\N	f
676	test_async_1773591021	$2b$12$gUJd0RnczsgPHTo3G4rLe.rKrv/BwtC13zI.WGKZOQYLDAzbbwW5S	test_async_1773591021@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 01:10:21.515651	\N	\N	\N	f
677	auth_test_1773591021	$2b$12$VoImaAIhXWu4bQL0K1tjWewyVPMgFzDM6hPGX0pBWi5VonpCjM8ue	auth_test_1773591021@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 01:10:21.796844	\N	\N	\N	f
678	log_test_1773591021	$2b$12$j3NxPWULwtFnAEwm6LHVdeIhIBBnBdRRP2RgKx8MC/ocO4D7QTz5C	log_test_1773591021@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 01:10:22.062629	\N	\N	\N	f
679	session_test_1773591022	$2b$12$7s8uYPGJ4KDfV.38t8Zto.O1F51OXv6a/ppBFuyPCFFJrEDavvrj.	session_test_1773591022@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 01:10:22.447549	\N	\N	\N	f
680	session_update_1773591022	$2b$12$u5j8ML4ChvF.vDka8Ftp6es8vUQBb0rRx9fBkQx4u9jvV51PdYVE.	session_update_1773591022@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 01:10:22.795584	\N	\N	\N	f
681	session_filter_1773591022	$2b$12$DnEsI5lmhO2K7429hI7GX.6jn.HXd95u6iDDe2.3WiAOdZha4OwFK	session_filter_1773591022@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 01:10:23.141775	\N	\N	\N	f
682	hashtest_9abfecc8	$2b$12$MlUFgqssoX6XEi5egs7.PuRpBtLNdxZ2qS.IXTr/saguNGzz/xOja	hash_9abfecc8@test.com	\N	\N	\N	\N	user	t	2026-03-16 01:10:23.474105	\N	\N	\N	f
683	admin_test_5e475958	admin_hash	admin_5e475958@test.com	\N	\N	\N	\N	admin	t	2026-03-16 01:10:23.729923	\N	\N	\N	f
684	deactivate_88fd6b85	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 01:10:23.780611	\N	\N	\N	f
685	sessiontest_316fce07	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:23.850498	\N	\N	\N	f
686	multisession_f45c8596	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:23.92306	\N	\N	\N	f
687	endsession_ca4fba1e	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:23.994004	\N	\N	\N	f
688	activity_d606f193	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:24.118297	\N	\N	\N	f
689	findactive_ac7fabfa	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:24.312422	\N	\N	\N	f
690	loginuser_422965a8	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:24.389388	\N	2026-03-16 01:10:24.413745	\N	f
691	createsession_0444bd90	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:24.462682	\N	2026-03-16 01:10:24.48431	\N	f
692	plaintext_test_1224971e	$2b$12$3LlD9zVaU7JghHDUQiZFauKygqRdNWWHnLATrr9ioHXh6gah318o2	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:24.734899	\N	\N	\N	f
693	user1_f2133957	$2b$12$esbE3mOtcMHjfe5NQ6EYWeTSD/.4X4XxyStNoltZ429fxbPEJTnn6	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:25.202561	\N	\N	\N	f
694	user2_f2133957	$2b$12$deOWQkLciobr37vQYeQS5umkG2QtziBVe7pjvwWqS4sNvHOitvul6	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:25.202565	\N	\N	\N	f
695	user_user_a50bec92	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:25.668538	\N	\N	\N	f
696	admin_user_a50bec92	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:10:25.668543	\N	\N	\N	f
697	superadmin_user_a50bec92	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 01:10:25.668544	\N	\N	\N	f
698	norole_f0f27a4b	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:25.736154	\N	\N	\N	f
699	mixed_4eb2cb95_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:10:25.790146	\N	\N	\N	f
700	mixed_4eb2cb95_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:10:25.79015	\N	\N	\N	f
701	mixed_4eb2cb95_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:25.790152	\N	\N	\N	f
702	mixed_4eb2cb95_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:25.790153	\N	\N	\N	f
703	mixed_4eb2cb95_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:10:25.790155	\N	\N	\N	f
708	dept_user_1773591139_0	$2b$12$N4ocGVVNe/rR6cigMwf6yO4yK4X832dRhEeErfbLj0cvplLjLcdha	dept_user_1773591139_0@example.com	Dept User 0	TestDept_1773591139	\N	\N	user	t	2026-03-16 01:12:19.575873	\N	\N	\N	f
709	dept_user_1773591139_1	$2b$12$x9awtCWTHFM9k6SXEmfVh.VeajvWNYd27EERRf1px63pOf0It0eFG	dept_user_1773591139_1@example.com	Dept User 1	TestDept_1773591139	\N	\N	user	t	2026-03-16 01:12:19.77482	\N	\N	\N	f
2	admin	$2b$12$4ZKYgKN3Wap0sR72PGRa9OA3/6DHcTNC16q4VrR9tVM2Ckguvl8sG	admin@company.com	System Administrator	IT	\N	\N	superadmin	t	2025-12-16 01:18:57.104168	\N	2026-03-17 01:28:49.542646	\N	f
704	auth_user_1773591137	$2b$12$cIp2TY6GWkLFMiK4z5AiYukuJM2562oHQ1R5GuDSwU34JJC3yMc9G	auth_user_1773591137@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 01:12:18.015594	\N	\N	\N	f
705	regular_user_1773591138	$2b$12$87H3mwxr0fSzjPwsnRqsU.DDdfFRXexGsPtndrsx60mHkuFXjBH7u	regular_1773591138@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 01:12:18.696522	\N	\N	\N	f
706	admin_user_1773591138	$2b$12$/sOfYqiURn9g7QmyNlymruPy9.62TQ0QJKvrKHdRX4ciUyr2zR8eq	admin_1773591138@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 01:12:18.895545	\N	\N	\N	f
714	auth_test_1773591140	$2b$12$yBv31B1j7HJlfSqdFLrnROWT0sX5YMzlxeItANm.JWJf8snw137RO	auth_test_1773591140@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 01:12:21.126626	\N	\N	\N	f
710	dept_user_1773591139_2	$2b$12$76sJZ6i5eNzxHt3aGSt9A.wp2rufPCD2s9okgMrR94MWEfj9W.6xi	dept_user_1773591139_2@example.com	Dept User 2	TestDept_1773591139	\N	\N	user	t	2026-03-16 01:12:19.974543	\N	\N	\N	f
711	unique_test_1773591140	$2b$12$O.IRTiv4b.p0uMnvLw5LL.FRuTSztStPdl.CUmzvIS70H.5sPZT42	unique_1773591140@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 01:12:20.211635	\N	\N	\N	f
712	login_test_1773591140	$2b$12$HiurwAohs.cppi.aLF/nYuJb2eYTdzL0WdDDFBlgY4/Pz2SmPa9nS	login_test_1773591140@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 01:12:20.485169	\N	2026-03-16 01:12:20.558844	\N	f
713	test_async_1773591140	$2b$12$enBf95i48p6OdaWmCsznA.Tmb7S4scOnOPK1/yg8li8PnYa4ok4Fi	test_async_1773591140@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 01:12:20.844509	\N	\N	\N	f
715	log_test_1773591141	$2b$12$mC51vnW13x1lg8AG6Ob.hupPU2E6/ynwbwJyl0ihB0FbdyVtnKg5G	log_test_1773591141@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 01:12:21.397955	\N	\N	\N	f
716	session_test_1773591141	$2b$12$o5uYEeWiJiHazVPACQ5Hc.uus5eIKXf8nbvKN9bBfeW08q5B1GW/y	session_test_1773591141@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 01:12:21.766389	\N	\N	\N	f
717	session_update_1773591141	$2b$12$xziAhBAOTwdvR1WnzSz52.NDgqMMOUdLkA7F5.hNvhpwNuuLA0sMu	session_update_1773591141@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 01:12:22.11828	\N	\N	\N	f
718	session_filter_1773591142	$2b$12$YlfravN94G1Nl8ngW2TumuuzF5cmuKrdosgpmCF4VExRT73ThWIpO	session_filter_1773591142@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 01:12:22.468067	\N	\N	\N	f
719	hashtest_e7661af4	$2b$12$m2/BK9.fizhn.Yv4OI0syOltr6VJ88RycU08ngY1cMeMN5UvjLHje	hash_e7661af4@test.com	\N	\N	\N	\N	user	t	2026-03-16 01:12:22.840621	\N	\N	\N	f
720	admin_test_66148a24	admin_hash	admin_66148a24@test.com	\N	\N	\N	\N	admin	t	2026-03-16 01:12:23.102603	\N	\N	\N	f
721	deactivate_f8b934fe	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 01:12:23.165744	\N	\N	\N	f
722	sessiontest_30eef5ba	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:23.242702	\N	\N	\N	f
723	multisession_2c2a5617	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:23.325013	\N	\N	\N	f
724	endsession_535b5d9a	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:23.605541	\N	\N	\N	f
725	activity_9279262c	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:23.70921	\N	\N	\N	f
726	findactive_b8caba97	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:23.912212	\N	\N	\N	f
727	loginuser_5d0e4419	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:23.995945	\N	2026-03-16 01:12:24.018889	\N	f
728	createsession_0898fd8e	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:24.070076	\N	2026-03-16 01:12:24.099687	\N	f
729	plaintext_test_2f674d84	$2b$12$WBtJA9YhlI.x5J0ik3l4lOM1qwQD7e29II09a1icf.6tnIXjjbP2y	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:24.365029	\N	\N	\N	f
730	user1_8d49b1d0	$2b$12$eWqKjdYqdHcdtyproxRyF.unUkWgm5hhGnysMC9vq1MEcVKHS2yKW	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:24.824834	\N	\N	\N	f
731	user2_8d49b1d0	$2b$12$s2UqXSb.h03X1uwX0C3DSu.LbjU0nkFYBDEO9gf/Gr7rMMsF4l4S2	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:24.824839	\N	\N	\N	f
732	user_user_30f83439	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:25.298999	\N	\N	\N	f
733	admin_user_30f83439	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:12:25.299003	\N	\N	\N	f
734	superadmin_user_30f83439	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 01:12:25.299004	\N	\N	\N	f
735	norole_bce020dd	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:25.359445	\N	\N	\N	f
736	mixed_bcb46ad8_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:12:25.422186	\N	\N	\N	f
737	mixed_bcb46ad8_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:12:25.422191	\N	\N	\N	f
738	mixed_bcb46ad8_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:25.422192	\N	\N	\N	f
739	mixed_bcb46ad8_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:25.422194	\N	\N	\N	f
740	mixed_bcb46ad8_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:12:25.422195	\N	\N	\N	f
741	auth_user_1773592303	$2b$12$lNEjdkufzXU4lYb7szUvn.QoWDQy.wDLuJti5aIrgOYUBlU.DQCC2	auth_user_1773592303@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 01:31:43.603681	\N	\N	\N	f
742	regular_user_1773592304	$2b$12$IdyajsMaSRH/1IM/91fQVuLxw/fDD5xZl8DhPBpSkCW10kwaq0yoe	regular_1773592304@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 01:31:44.381643	\N	\N	\N	f
743	admin_user_1773592304	$2b$12$kDmgxWpM9CXIMFy6u87k9./X.HSCZW7hiZjFaodiuRJCtD3MoNvLm	admin_1773592304@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 01:31:44.582306	\N	\N	\N	f
763	findactive_6f67d717	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:50.163578	\N	\N	\N	f
744	activation_test_1773592304	$2b$12$/6Cl.5y3pHDnP/Nb5L/aMeWjvOLM1HKezFDmY4fKBoAB52tmF2YRe	activation_1773592304@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 01:31:44.880454	\N	\N	\N	f
745	dept_user_1773592305_0	$2b$12$0veeXGddsVY3RFIehfNTludWdVgYU6NZ3S3mSE7sKeOJF6UdwfPgO	dept_user_1773592305_0@example.com	Dept User 0	TestDept_1773592305	\N	\N	user	t	2026-03-16 01:31:45.379624	\N	\N	\N	f
746	dept_user_1773592305_1	$2b$12$HEnADNRYWgxuzOK4RE0xXeXkMTn5FQ6.Kwb0sSGJoToz7ydsJr6Ya	dept_user_1773592305_1@example.com	Dept User 1	TestDept_1773592305	\N	\N	user	t	2026-03-16 01:31:45.580631	\N	\N	\N	f
747	dept_user_1773592305_2	$2b$12$2QG6KC4EKChCQIdQ8W7hqOIioyJRAeZDd8w4hyJDDMHvZXwUf1QjO	dept_user_1773592305_2@example.com	Dept User 2	TestDept_1773592305	\N	\N	user	t	2026-03-16 01:31:45.781299	\N	\N	\N	f
748	unique_test_1773592305	$2b$12$Xv9p9WIGcj1rBV0JlXlNCeLbyXeUX.DZ9wUSF9a84U47Sn6xFTf3a	unique_1773592305@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 01:31:46.044194	\N	\N	\N	f
749	login_test_1773592306	$2b$12$mmL4HprW5LiBioHeXsMHN.lJaGzpO6hCLAix3TutO.OAADMI8bNJO	login_test_1773592306@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 01:31:46.358173	\N	2026-03-16 01:31:46.463073	\N	f
750	test_async_1773592306	$2b$12$FzkjtdknLfYtkqaH3ytxN.tOEtIyibaFbPekhwd0NwumTSKCDvfjW	test_async_1773592306@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 01:31:46.788259	\N	\N	\N	f
751	auth_test_1773592306	$2b$12$ykbjjJK0ylQT.Q9SvZbmYefrjazmeE8X/yZQW5DrCv52aBJ9h5T6C	auth_test_1773592306@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 01:31:47.088966	\N	\N	\N	f
752	log_test_1773592307	$2b$12$aYyvo2ErCV90VDxQxKm5iOG0ECYqcZx1PCMNnpj8RVo0NZsUi7TBy	log_test_1773592307@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 01:31:47.385562	\N	\N	\N	f
753	session_test_1773592307	$2b$12$SSP5kEKhMNPOy7YHOFqbPO31PThOccWjWM5mNBUfDsGtHJyTmvSm.	session_test_1773592307@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 01:31:47.764062	\N	\N	\N	f
754	session_update_1773592307	$2b$12$Ii0s37TzssM7pHSKyzPMIuHHyc83EXy1bu3DmIiTxWf693cS6wwg6	session_update_1773592307@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 01:31:48.134269	\N	\N	\N	f
755	session_filter_1773592308	$2b$12$aZXUCRgncCvnGtbuH20Du.m9DG6ykx9/L2Xs.kSZ5e6uIWDk0HOYm	session_filter_1773592308@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 01:31:48.541244	\N	\N	\N	f
756	hashtest_557f3499	$2b$12$bjaKPn3uhMk1oS5rKR4Go.o457rLmn1KZniD3G70uEsyPhs7jzDxi	hash_557f3499@test.com	\N	\N	\N	\N	user	t	2026-03-16 01:31:49.232168	\N	\N	\N	f
757	admin_test_416ba40b	admin_hash	admin_416ba40b@test.com	\N	\N	\N	\N	admin	t	2026-03-16 01:31:49.486949	\N	\N	\N	f
758	deactivate_65652907	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 01:31:49.552655	\N	\N	\N	f
759	sessiontest_e590ee4e	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:49.637609	\N	\N	\N	f
760	multisession_2592fc81	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:49.730207	\N	\N	\N	f
761	endsession_e9b4d5aa	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:49.830506	\N	\N	\N	f
762	activity_ea4da9d1	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:49.9412	\N	\N	\N	f
764	loginuser_f13a0969	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:50.263467	\N	2026-03-16 01:31:50.29028	\N	f
765	createsession_81a3bae4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:50.35644	\N	2026-03-16 01:31:50.379458	\N	f
766	plaintext_test_ca8c8ed5	$2b$12$1J6e9266TWbvco12LPJa3u67s16KG8tiIrRrjr7f9eyhdh.QD9T4W	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:50.652665	\N	\N	\N	f
767	user1_f1b60d2a	$2b$12$cZtI.x87iq8qUPU7qUzecOpvBf39fQ.NIwypq8M02nzFb3GglHF32	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:51.121462	\N	\N	\N	f
768	user2_f1b60d2a	$2b$12$aEDQK8OntwLp.z0GAWmPIOkIQFWG.Ys2.tRNUFhmXlEGhp2VTrz7.	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:51.121466	\N	\N	\N	f
769	user_user_daaef9f1	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:51.602808	\N	\N	\N	f
770	admin_user_daaef9f1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:31:51.602829	\N	\N	\N	f
771	superadmin_user_daaef9f1	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 01:31:51.602831	\N	\N	\N	f
772	norole_ef1744ef	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:51.659506	\N	\N	\N	f
773	mixed_23d70803_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:31:51.726519	\N	\N	\N	f
774	mixed_23d70803_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:31:51.726523	\N	\N	\N	f
775	mixed_23d70803_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:51.726525	\N	\N	\N	f
776	mixed_23d70803_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:51.726526	\N	\N	\N	f
777	mixed_23d70803_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:31:51.726528	\N	\N	\N	f
778	auth_user_1773593452	$2b$12$nX4mTscdGtrqGr4vj5dph.5/v8kNso3ukCi6g4QpMWDJqSgvCBkya	auth_user_1773593452@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 01:50:53.196488	\N	\N	\N	f
779	regular_user_1773593453	$2b$12$jovQ0M8XLc8Dq4OpBEskA.gEztJK4Iv8guoPRwNFkegGcRyc8V0L2	regular_1773593453@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 01:50:53.952554	\N	\N	\N	f
780	admin_user_1773593453	$2b$12$0sjeha.Vk1ifwigSZN1hROXm51yNUNVmTVyz4A2mAh9Ytlbn.WLMq	admin_1773593453@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 01:50:54.154122	\N	\N	\N	f
819	dept_user_1773593839_0	$2b$12$G0krYfVYgezraxBUSINnjO0HNb7DRwpfLzSuvEL.JCZ0R/0VpPIH2	dept_user_1773593839_0@example.com	Dept User 0	TestDept_1773593839	\N	\N	user	t	2026-03-16 01:57:20.113683	\N	\N	\N	f
781	activation_test_1773593454	$2b$12$6LJXV2RC5Mf0bOHWXBHjs.o1YpMyVZDM1pdpwXjsvDWlidCZltuaC	activation_1773593454@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 01:50:54.479456	\N	\N	\N	f
782	dept_user_1773593454_0	$2b$12$9CqPDF0yqHpPcNh7uuDQG.SqZA7mLSkuiPPb0sk9iMiuXkze71Qky	dept_user_1773593454_0@example.com	Dept User 0	TestDept_1773593454	\N	\N	user	t	2026-03-16 01:50:54.963401	\N	\N	\N	f
783	dept_user_1773593454_1	$2b$12$g/EtmGBDyKTLhiq2ttbuQOj59fMHKjqqUxFCENggPdYlk3MT7UCX2	dept_user_1773593454_1@example.com	Dept User 1	TestDept_1773593454	\N	\N	user	t	2026-03-16 01:50:55.162855	\N	\N	\N	f
784	dept_user_1773593454_2	$2b$12$Hh0B2Wj8Y0xBrZtTGizjM.EtFPOUiLMDJ/gYXLdJT85RKjT5eqyGG	dept_user_1773593454_2@example.com	Dept User 2	TestDept_1773593454	\N	\N	user	t	2026-03-16 01:50:55.36268	\N	\N	\N	f
785	unique_test_1773593455	$2b$12$6si.PxiRM6jMBi0f8F9q1ezq/JruRYyPbhL0XbDmgl4TBVy/Bpjiu	unique_1773593455@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 01:50:55.65622	\N	\N	\N	f
786	login_test_1773593455	$2b$12$LUeehwZCqVXapeT4miWaEe.hma1xynwXgHstJGZzZG57Sqz4sNSDy	login_test_1773593455@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 01:50:56.008906	\N	2026-03-16 01:50:56.158382	\N	f
787	test_async_1773593456	$2b$12$W90SGtfTMU7mGDXzVUWqOeQjfXEsX.ToWbqIGYvWbNsBgHHOJSRbK	test_async_1773593456@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 01:50:56.456274	\N	\N	\N	f
788	auth_test_1773593456	$2b$12$SFGiHftjFV42hBjdLLRRWeUBlHHFS1MnGTha3TfubDeh1srr7Nioa	auth_test_1773593456@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 01:50:56.799958	\N	\N	\N	f
789	log_test_1773593456	$2b$12$MZymc63DXMC2TXqNNz4zWOx8ikRcm9TKkeYC/MAXSPrmp3Y0783Lm	log_test_1773593456@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 01:50:57.109139	\N	\N	\N	f
790	session_test_1773593457	$2b$12$vPkub.Aj5z.a.miRB5DSPOLlZ0L3ak5accZuMMJQSs4e5d4uvC.Z6	session_test_1773593457@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 01:50:57.533634	\N	\N	\N	f
791	session_update_1773593457	$2b$12$OTvk8Y4WoRX.Sih3m6LuPez/BiU3YXwlcW0QbtMAq3DDYhDAd8mGG	session_update_1773593457@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 01:50:57.967965	\N	\N	\N	f
792	session_filter_1773593458	$2b$12$AXTk6jeMNECcpusjQ4AlJOgjzuCIubRE/cHNr0InMqdQW8caWvMtO	session_filter_1773593458@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 01:50:58.46746	\N	\N	\N	f
793	hashtest_73ed0a39	$2b$12$tC0KTEx7Zf0X3sxDkGV6NuEJTok1oInaSf/AJF3UQBpQ/FHPZYL72	hash_73ed0a39@test.com	\N	\N	\N	\N	user	t	2026-03-16 01:50:58.856237	\N	\N	\N	f
794	admin_test_cd371d9b	admin_hash	admin_cd371d9b@test.com	\N	\N	\N	\N	admin	t	2026-03-16 01:50:59.152789	\N	\N	\N	f
795	deactivate_44f84227	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 01:50:59.257786	\N	\N	\N	f
796	sessiontest_f43696db	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.408778	\N	\N	\N	f
797	multisession_91d8ac29	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.558944	\N	\N	\N	f
798	endsession_4eb33404	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.730571	\N	\N	\N	f
799	activity_327ea0b0	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.950055	\N	\N	\N	f
800	findactive_890dee91	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:51:00.271146	\N	\N	\N	f
801	loginuser_cbca3dfd	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:51:00.42537	\N	2026-03-16 01:51:00.480083	\N	f
802	createsession_4f5fc381	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:51:00.597153	\N	2026-03-16 01:51:00.649089	\N	f
803	plaintext_test_e2d9e360	$2b$12$OeqMpwlH8x7EiqMurQp/XOCI4s/qzwp2YcsxLaJGRQYZIWx/zzlia	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:58.527827	\N	\N	\N	f
804	user1_dc12adea	$2b$12$oYTcad96VBFPowGIKW498.Jj1eAcEWWPxNoxf7dcHeIdT30kaoRqe	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.016873	\N	\N	\N	f
805	user2_dc12adea	$2b$12$XPnhAHT8XJAZliTM8Dyfk.jV0IQkou/oY.hYjQyv1iWtWweT94aAm	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.016878	\N	\N	\N	f
806	user_user_32e9cc69	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.505982	\N	\N	\N	f
807	admin_user_32e9cc69	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:50:59.505986	\N	\N	\N	f
808	superadmin_user_32e9cc69	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 01:50:59.505987	\N	\N	\N	f
809	norole_67b394f7	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.589622	\N	\N	\N	f
810	mixed_2eb3c368_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:50:59.67068	\N	\N	\N	f
811	mixed_2eb3c368_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:50:59.670684	\N	\N	\N	f
812	mixed_2eb3c368_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.670686	\N	\N	\N	f
813	mixed_2eb3c368_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.670687	\N	\N	\N	f
814	mixed_2eb3c368_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:50:59.670689	\N	\N	\N	f
815	auth_user_1773593838	$2b$12$0ojAbsj1eTfEROQGOAiXFun2EehIjzgoJsoNIMel/kHIwDx6IGn2W	auth_user_1773593838@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 01:57:18.272304	\N	\N	\N	f
816	regular_user_1773593838	$2b$12$LEVt676AdamjIqBrEtjpYehKEAtmwX410EAXT4hgccD6mpuIqt44y	regular_1773593838@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 01:57:19.060807	\N	\N	\N	f
817	admin_user_1773593838	$2b$12$CCSjWoKHz4A5ODzhUnvYX.F/8Ke1G8JbHY3dJtiHv19XRYJsE4WlS	admin_1773593838@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 01:57:19.266018	\N	\N	\N	f
820	dept_user_1773593839_1	$2b$12$aSsuW/RHe7EWc2OYEkm/o.4n.vjYbb.PozQrvJ.dYXD4ys4QXGhny	dept_user_1773593839_1@example.com	Dept User 1	TestDept_1773593839	\N	\N	user	t	2026-03-16 01:57:20.31801	\N	\N	\N	f
818	activation_test_1773593839	$2b$12$cgyWQxs1Sd6xSJ7px.Bfp.OrRMEbGo5mb7PjtBr07JAmjSl3mMBKu	activation_1773593839@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 01:57:19.564668	\N	\N	\N	f
821	dept_user_1773593839_2	$2b$12$h3JCZ6lZ2TBauEiFVwvYS.vBC..no0zri6l3c5KBiBRDHUe.gRyKW	dept_user_1773593839_2@example.com	Dept User 2	TestDept_1773593839	\N	\N	user	t	2026-03-16 01:57:20.522266	\N	\N	\N	f
822	unique_test_1773593840	$2b$12$x7Kr9gu8YF5c8QpEQSnAA.Winf3haxxzH/TS8/xFTHRvyrF0IyUFq	unique_1773593840@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 01:57:20.823344	\N	\N	\N	f
823	login_test_1773593841	$2b$12$PYTcTyhHAeVKW93AQ9939.bek.8Kz5VSn95JZb26VJwY.IwGS/yZW	login_test_1773593841@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 01:57:21.271485	\N	2026-03-16 01:57:21.443316	\N	f
824	test_async_1773593841	$2b$12$FbHTR81g/5w1PEsUfwvjl.DgFxU6Wk4WcxhUtCNXpk4XQENXBpOAq	test_async_1773593841@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 01:57:21.74191	\N	\N	\N	f
825	auth_test_1773593841	$2b$12$UmFONvs7ZxrD/2YkQ6nj7uumfVacIJr.PTB0U/zADlii94WX/2Tdi	auth_test_1773593841@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 01:57:22.091032	\N	\N	\N	f
826	log_test_1773593842	$2b$12$ddXBm75hqGIiIuJix4bqn.uPEmDGtTZsRQ8X5p1FBbo5xxg2jSZLC	log_test_1773593842@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 01:57:22.579392	\N	\N	\N	f
827	session_test_1773593842	$2b$12$sj.RfwqaAnqwYvArvBYhnOr9cxLHox4We8qO2akmC1z526S2Oup42	session_test_1773593842@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 01:57:23.043686	\N	\N	\N	f
828	session_update_1773593843	$2b$12$lw29IgrWUQmMiqQK3mxSNuOPwmxhvZkoIny5r44FdxXAxS77WPCiq	session_update_1773593843@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 01:57:23.467919	\N	\N	\N	f
829	session_filter_1773593843	$2b$12$CpqYhziIN7IKr1X6OwC6j.3y0dXqolIwKC5VeGlk1LEynWO6IOec6	session_filter_1773593843@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 01:57:24.02339	\N	\N	\N	f
830	hashtest_72f41dc5	$2b$12$0nxep62HKeszjyrWBhQ9CuaH.9qqnU/38PY6IRnpiAwP.xAU1juwi	hash_72f41dc5@test.com	\N	\N	\N	\N	user	t	2026-03-16 01:57:24.445992	\N	\N	\N	f
831	admin_test_25ec2caf	admin_hash	admin_25ec2caf@test.com	\N	\N	\N	\N	admin	t	2026-03-16 01:57:24.761711	\N	\N	\N	f
832	deactivate_6bd3e1f8	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 01:57:24.888795	\N	\N	\N	f
833	sessiontest_405fdcd5	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:25.032815	\N	\N	\N	f
834	multisession_228fc041	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:25.217519	\N	\N	\N	f
835	endsession_f7b46f0f	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:25.420162	\N	\N	\N	f
836	activity_945a08d8	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:25.69797	\N	\N	\N	f
837	findactive_6d1512a1	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:26.086489	\N	\N	\N	f
838	loginuser_2945e9e9	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:26.295997	\N	2026-03-16 01:57:26.342483	\N	f
839	createsession_26229cb1	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:26.51321	\N	2026-03-16 01:57:26.56591	\N	f
840	plaintext_test_cf5744fa	$2b$12$KhrEyBR4Bz8/L.4pQK0XeO/C2h3jcT2RO/zTsTsgGQM3qMcaL9oO6	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:26.869609	\N	\N	\N	f
841	user1_1a0333b4	$2b$12$CRx9fmCPGU6PD.W43YyEHOgvAac735/qMXZaAFT3OXLwvx7d11QSm	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:27.347767	\N	\N	\N	f
842	user2_1a0333b4	$2b$12$kNdFbVz2sdRjAvTfHLC8G.cwAVk1VJRydhiqH.5.WA.ErCiRCHYBm	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:27.347771	\N	\N	\N	f
843	user_user_5cb67c81	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:27.858623	\N	\N	\N	f
844	admin_user_5cb67c81	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:57:27.858625	\N	\N	\N	f
845	superadmin_user_5cb67c81	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 01:57:27.858625	\N	\N	\N	f
846	norole_1192c042	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:27.973548	\N	\N	\N	f
847	mixed_da9dec6c_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:57:28.088018	\N	\N	\N	f
848	mixed_da9dec6c_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 01:57:28.088021	\N	\N	\N	f
849	mixed_da9dec6c_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:28.088021	\N	\N	\N	f
850	mixed_da9dec6c_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:28.088021	\N	\N	\N	f
851	mixed_da9dec6c_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 01:57:28.088022	\N	\N	\N	f
852	auth_user_1773596246	$2b$12$.EplTSrpGkVvPvvaOqk0KeldnXHTabC8LDGl0LuHvBHUnfUa254E2	auth_user_1773596246@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 02:37:26.987377	\N	\N	\N	f
853	regular_user_1773596247	$2b$12$V.t0FXPfbhOChdBZOV6koOTkejmJQ7YQ2JfA7geOVli6z0X6I7A8O	regular_1773596247@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 02:37:27.705368	\N	\N	\N	f
854	admin_user_1773596247	$2b$12$sTY1DQ1kW47TQP/pTNobUOoXNEmzvlWGW4ZFLGyDeS.I5d50o1s6S	admin_1773596247@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 02:37:27.911813	\N	\N	\N	f
872	endsession_1188635b	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:36.83642	\N	\N	\N	f
855	activation_test_1773596247	$2b$12$1Fl/24oISXSNhQzIJ.Tt4OeINZWLxZUC7.kimx6gD3vvyBtUqh3rS	activation_1773596247@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 02:37:28.19846	\N	\N	\N	f
856	dept_user_1773596248_0	$2b$12$MsZyMSPG8HKFufoy25lXtefZFsx0rub82zTdwvHO.mvboNCXBy9CC	dept_user_1773596248_0@example.com	Dept User 0	TestDept_1773596248	\N	\N	user	t	2026-03-16 02:37:29.083046	\N	\N	\N	f
857	dept_user_1773596248_1	$2b$12$b.iMoRC7ejIZ0J.TgrAcWeFljpoWoOQ5cIeTRD0dJco/w4kS035qW	dept_user_1773596248_1@example.com	Dept User 1	TestDept_1773596248	\N	\N	user	t	2026-03-16 02:37:29.288439	\N	\N	\N	f
858	dept_user_1773596248_2	$2b$12$jWUE4MuvWI5v0H00OtPIJOcYY6/Fk.6fhTsGenyRKpSCwg4nCQ84G	dept_user_1773596248_2@example.com	Dept User 2	TestDept_1773596248	\N	\N	user	t	2026-03-16 02:37:29.494846	\N	\N	\N	f
859	unique_test_1773596249	$2b$12$weAaQiyll/wF7vpRrVpYd.melXPUgZeRqldoSGBKngUUKM80ofci.	unique_1773596249@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 02:37:29.920125	\N	\N	\N	f
860	login_test_1773596250	$2b$12$XkymIiizTn0vhMZ/PHFEOu5.t0weEcVQcPTnBDIRZnD/dLI83JxKK	login_test_1773596250@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 02:37:30.593664	\N	2026-03-16 02:37:30.676006	\N	f
861	test_async_1773596250	$2b$12$JTFXzHYqE7hqJlavbKYWHuNwCARXKYtAcIc.fgdBB4uxSKcVXn0OG	test_async_1773596250@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 02:37:30.953766	\N	\N	\N	f
862	auth_test_1773596251	$2b$12$HYabY/T1gnLBCjG0i6Wiqe9NHAmGLCdN7W1VI7iO0fGOZ5ll7ddyC	auth_test_1773596251@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 02:37:31.227728	\N	\N	\N	f
863	log_test_1773596251	$2b$12$GSLlfGT5rI3Q2lKpa1GJDeJFzCgh1BhFlcHL8Xj.rblh8SjfAOc.y	log_test_1773596251@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 02:37:31.702609	\N	\N	\N	f
864	session_test_1773596252	$2b$12$V97/1PXd7hcHmJJF/pT.wOGpzgBQg148Am3XVzaZyEthnvoTojF/S	session_test_1773596252@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 02:37:32.445949	\N	\N	\N	f
865	session_update_1773596252	$2b$12$IUR8awRccY2X8CyB/xgzjuBt71CrsLKWgY3sA6gm9merBi8R/gqlS	session_update_1773596252@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 02:37:33.182017	\N	\N	\N	f
866	session_filter_1773596253	$2b$12$LdXSS9SWNARvVe2mNO2FF.GhjJTi4cd9G.KLx921JL44J4mrzoz3O	session_filter_1773596253@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 02:37:34.173874	\N	\N	\N	f
867	hashtest_fa9d2b5f	$2b$12$skkC5w9CkEMUz6VhKHuPIOdOlnmtaUXVLUC09ScS3mnUmEO8xbzle	hash_fa9d2b5f@test.com	\N	\N	\N	\N	user	t	2026-03-16 02:37:34.91374	\N	\N	\N	f
868	admin_test_9920f79f	admin_hash	admin_9920f79f@test.com	\N	\N	\N	\N	admin	t	2026-03-16 02:37:35.459294	\N	\N	\N	f
869	deactivate_23d3d41d	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 02:37:35.638639	\N	\N	\N	f
870	sessiontest_5d05cf15	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:36.042103	\N	\N	\N	f
871	multisession_95916779	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:36.434494	\N	\N	\N	f
873	activity_546c0fff	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:37.447251	\N	\N	\N	f
874	findactive_c32d81ed	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:38.155716	\N	\N	\N	f
875	loginuser_a1c5ddc4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:38.720234	\N	2026-03-16 02:37:38.954086	\N	f
876	createsession_e3798862	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:39.205446	\N	2026-03-16 02:37:39.484828	\N	f
877	plaintext_test_a1957e59	$2b$12$mSBSZk52tiLoNG7BKdtxK.ic/HPOndwbDQDv0Hd0iS5vN1kk/0NFC	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:39.907945	\N	\N	\N	f
878	user1_fb0c0471	$2b$12$fUbhXT9wnTDQV1P6OvrPKulhE5SVALzM4zeJcYPLS9nGq/..sdTbm	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:40.652116	\N	\N	\N	f
879	user2_fb0c0471	$2b$12$5RUv.bZZBhdeXiOQ6ezj9ukcVRKyn6ze63oMMTVXHKZ/FdyiMO/qe	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:40.652118	\N	\N	\N	f
880	user_user_b218c083	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:41.1114	\N	\N	\N	f
881	admin_user_b218c083	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 02:37:41.111403	\N	\N	\N	f
882	superadmin_user_b218c083	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 02:37:41.111403	\N	\N	\N	f
883	norole_cb00684d	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:41.173416	\N	\N	\N	f
884	mixed_bb8a6d05_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 02:37:41.230291	\N	\N	\N	f
885	mixed_bb8a6d05_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 02:37:41.230294	\N	\N	\N	f
886	mixed_bb8a6d05_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:41.230295	\N	\N	\N	f
887	mixed_bb8a6d05_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:41.230295	\N	\N	\N	f
888	mixed_bb8a6d05_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:37:41.230296	\N	\N	\N	f
889	auth_user_1773596441	$2b$12$5MVQGuYO72mLjsBG4dXqVOZdu33LgBB7rZjOayJmsVz14dAhU9.VC	auth_user_1773596441@example.com	Auth Test User	Testing	\N	\N	user	t	2026-03-16 02:40:41.328952	\N	\N	\N	f
890	regular_user_1773596441	$2b$12$TqAh53Uja.CSay8TgeVH0e5z8g20yr9ucfr3L94KfKD4J/vJCf79a	regular_1773596441@example.com	Regular User	Testing	\N	\N	user	t	2026-03-16 02:40:42.066779	\N	\N	\N	f
891	admin_user_1773596441	$2b$12$5MTnnefQwdv0jFWf2ALwFu2nH0mfdZeM1q1i8o7Ggm1tZnOuxwCTi	admin_1773596441@example.com	Admin User	IT	\N	\N	admin	t	2026-03-16 02:40:42.267941	\N	\N	\N	f
892	activation_test_1773596442	$2b$12$1IkDe/7PJ9.lW6p4zL5Gx.8WZRr./Y1akiQdM8EfWvhGo8oQF22IK	activation_1773596442@example.com	Activation Test	Testing	\N	\N	user	t	2026-03-16 02:40:42.603138	\N	\N	\N	f
893	dept_user_1773596442_0	$2b$12$DaZOtiv7YSote6hcV4hkte/LdiIq4t1t0eJLU/um9G4koDYXoMowu	dept_user_1773596442_0@example.com	Dept User 0	TestDept_1773596442	\N	\N	user	t	2026-03-16 02:40:43.081034	\N	\N	\N	f
894	dept_user_1773596442_1	$2b$12$u0Z1z.SzpkFI0ORkI.41cejRpVT795xz0KXeNLdcNFInu.e07U4qO	dept_user_1773596442_1@example.com	Dept User 1	TestDept_1773596442	\N	\N	user	t	2026-03-16 02:40:43.284689	\N	\N	\N	f
895	dept_user_1773596442_2	$2b$12$3cUXM6HHn3VhZvA6JacoQuvSrX3ZI63enjz3rfkscGWHoSflft7eW	dept_user_1773596442_2@example.com	Dept User 2	TestDept_1773596442	\N	\N	user	t	2026-03-16 02:40:43.485989	\N	\N	\N	f
896	unique_test_1773596443	$2b$12$oBPO01B4v6PEwa/JrZWIM.7iyHTKEkAMwL8JXzd46XkkQ1jP4DyEG	unique_1773596443@example.com	Unique Test 1	Testing	\N	\N	user	t	2026-03-16 02:40:43.745941	\N	\N	\N	f
897	login_test_1773596443	$2b$12$AAJF.egQxLF6aGESptgVFuS5mS6zdQQQOUWDsH0wCB5fsqCt.Av8i	login_test_1773596443@example.com	Login Test	Testing	\N	\N	user	t	2026-03-16 02:40:44.065773	\N	2026-03-16 02:40:44.190374	\N	f
898	test_async_1773596444	$2b$12$1vk42vK3k.sFCWhcGS5sUOa3chEAeD.VKc3iCLaM88/h.USIQHGjm	test_async_1773596444@example.com	Async Test User	Testing	\N	\N	user	t	2026-03-16 02:40:44.504676	\N	\N	\N	f
899	auth_test_1773596444	$2b$12$JHfhRcy12PuyIX09.IK2TuqI5kfO0Yri9lKoxkStRimGqG/BCwVQa	auth_test_1773596444@example.com	Auth Test	Testing	\N	\N	user	t	2026-03-16 02:40:44.81728	\N	\N	\N	f
900	log_test_1773596444	$2b$12$.Ngzk.rrWKj1hQi9qoiIl.Swoj7mflvtZwEKHzd5n1blYuxDPzl0m	log_test_1773596444@example.com	Log Test User	Testing	\N	\N	user	t	2026-03-16 02:40:45.124541	\N	\N	\N	f
901	session_test_1773596445	$2b$12$/xwfpnzfcPQ77Z2pWgzbw.wiwp.e6aNl0SdtoRioeP0lY5ccnGrva	session_test_1773596445@example.com	Session Test User	Testing	\N	\N	user	t	2026-03-16 02:40:45.558053	\N	\N	\N	f
902	session_update_1773596445	$2b$12$a/V31JlkC8r7efxFoRQNp.oWeP8AHiPpHzVFR8rGNvWgbCaZAR2aW	session_update_1773596445@example.com	Session Update Test	Testing	\N	\N	user	t	2026-03-16 02:40:46.026083	\N	\N	\N	f
903	session_filter_1773596446	$2b$12$M9Tm.y7uPbmJyRtaczz7seS01omiCmfJn5GOnXJffPW0LfY7QKpDu	session_filter_1773596446@example.com	Session Filter Test	Testing	\N	\N	user	t	2026-03-16 02:40:46.556806	\N	\N	\N	f
904	hashtest_750f48a7	$2b$12$Yqt3U02Wc4cvLBxkn5A8xepUxl6LlWDB35NjMW8BP0kdu/Qjw4O7.	hash_750f48a7@test.com	\N	\N	\N	\N	user	t	2026-03-16 02:40:47.045202	\N	\N	\N	f
905	admin_test_68bcd927	admin_hash	admin_68bcd927@test.com	\N	\N	\N	\N	admin	t	2026-03-16 02:40:47.345785	\N	\N	\N	f
906	deactivate_c2e85d64	hash	\N	\N	\N	\N	\N	user	f	2026-03-16 02:40:47.430419	\N	\N	\N	f
907	sessiontest_e1c8b268	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:47.602285	\N	\N	\N	f
908	multisession_c64d3c1c	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:47.763579	\N	\N	\N	f
909	endsession_ab1ce8e8	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:47.898099	\N	\N	\N	f
910	activity_034e7353	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:48.110968	\N	\N	\N	f
911	findactive_9daef38f	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:48.454229	\N	\N	\N	f
912	loginuser_9f1dadc0	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:48.605082	\N	2026-03-16 02:40:48.685388	\N	f
913	createsession_1bb4ef9c	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:48.751257	\N	2026-03-16 02:40:48.811602	\N	f
914	plaintext_test_ead6858a	$2b$12$rzN0JPUqDG6AVbKLOwUhMO5DEwua/TEuMb7fxznyxWjxOpaRxbb8.	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:49.113589	\N	\N	\N	f
915	user1_f00eaa2c	$2b$12$b7UNXTEEe20YR5QL78mUpufKA02zIaNdskAGFUtwZtXGqM4sLpHmy	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:49.603051	\N	\N	\N	f
916	user2_f00eaa2c	$2b$12$fckW1LGEUuqbq21cX2eHOeKkVgp/eu514Z6Wpnf9gp6dRrWhnAqke	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:49.603055	\N	\N	\N	f
917	user_user_9ec5246b	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:50.108699	\N	\N	\N	f
918	admin_user_9ec5246b	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 02:40:50.108702	\N	\N	\N	f
919	superadmin_user_9ec5246b	hash	\N	\N	\N	\N	\N	superadmin	t	2026-03-16 02:40:50.108703	\N	\N	\N	f
920	norole_92f655e8	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:50.202107	\N	\N	\N	f
921	mixed_9f6cfa1e_0	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 02:40:50.290447	\N	\N	\N	f
922	mixed_9f6cfa1e_1	hash	\N	\N	\N	\N	\N	admin	t	2026-03-16 02:40:50.290451	\N	\N	\N	f
923	mixed_9f6cfa1e_2	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:50.290451	\N	\N	\N	f
924	mixed_9f6cfa1e_3	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:50.290452	\N	\N	\N	f
925	mixed_9f6cfa1e_4	hash	\N	\N	\N	\N	\N	user	t	2026-03-16 02:40:50.290452	\N	\N	\N	f
926	test_profile_631237	$2b$12$vNYO8ametJwWorMx0sxhJOjFCz1JQ8zk3v2t4z7k4.rQWZMVVZQoK	\N	Test User	\N	Team Alpha	Japanese	user	f	2026-03-16 03:21:15.279778	2	\N	\N	f
927	test_created_631237	$2b$12$jQPvlx8Jeoe9JA25NsLRzu1C.9TD6sdn0oShdNiLMuHGEHQAXsy6C	\N	\N	\N	\N	\N	user	f	2026-03-16 03:21:13.466098	2	\N	\N	f
928	test_fullprof_631237	$2b$12$h/EBW0UE33SJqi5YACgA9.Qxmgyk8L3HI8gxvXmQb8ZJsnlOcanj2	test_631237@example.com	Test Full Profile	Localization	Quality Team	Korean	user	f	2026-03-16 03:21:18.655438	2	\N	\N	f
\.


--
-- Name: active_operations_operation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.active_operations_operation_id_seq', 614, true);


--
-- Name: announcements_announcement_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.announcements_announcement_id_seq', 1, false);


--
-- Name: app_versions_version_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.app_versions_version_id_seq', 1, false);


--
-- Name: error_logs_error_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.error_logs_error_id_seq', 160, true);


--
-- Name: function_usage_stats_stat_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.function_usage_stats_stat_id_seq', 60, true);


--
-- Name: ldm_active_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_active_sessions_id_seq', 1, false);


--
-- Name: ldm_active_tms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_active_tms_id_seq', 6, true);


--
-- Name: ldm_backups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_backups_id_seq', 1, false);


--
-- Name: ldm_edit_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_edit_history_id_seq', 165, true);


--
-- Name: ldm_files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_files_id_seq', 308, true);


--
-- Name: ldm_folders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_folders_id_seq', 93, true);


--
-- Name: ldm_platforms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_platforms_id_seq', 128, true);


--
-- Name: ldm_projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_projects_id_seq', 283, true);


--
-- Name: ldm_qa_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_qa_results_id_seq', 830, true);


--
-- Name: ldm_resource_access_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_resource_access_id_seq', 8, true);


--
-- Name: ldm_rows_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_rows_id_seq', 224753, true);


--
-- Name: ldm_tm_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_tm_assignments_id_seq', 17, true);


--
-- Name: ldm_tm_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_tm_entries_id_seq', 43766, true);


--
-- Name: ldm_tm_indexes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_tm_indexes_id_seq', 1252, true);


--
-- Name: ldm_translation_memories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_translation_memories_id_seq', 466, true);


--
-- Name: ldm_trash_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.ldm_trash_id_seq', 230, true);


--
-- Name: log_entries_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.log_entries_log_id_seq', 388, true);


--
-- Name: performance_metrics_metric_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.performance_metrics_metric_id_seq', 320, true);


--
-- Name: remote_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.remote_logs_log_id_seq', 7, true);


--
-- Name: telemetry_summary_summary_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.telemetry_summary_summary_id_seq', 2, true);


--
-- Name: tool_usage_stats_stat_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.tool_usage_stats_stat_id_seq', 40, true);


--
-- Name: update_history_update_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.update_history_update_id_seq', 1, false);


--
-- Name: user_activity_summary_summary_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.user_activity_summary_summary_id_seq', 1, false);


--
-- Name: user_capabilities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.user_capabilities_id_seq', 1, false);


--
-- Name: user_feedback_feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.user_feedback_feedback_id_seq', 1, false);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: localization_admin
--

SELECT pg_catalog.setval('public.users_user_id_seq', 928, true);


--
-- Name: active_operations active_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.active_operations
    ADD CONSTRAINT active_operations_pkey PRIMARY KEY (operation_id);


--
-- Name: announcements announcements_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.announcements
    ADD CONSTRAINT announcements_pkey PRIMARY KEY (announcement_id);


--
-- Name: app_versions app_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.app_versions
    ADD CONSTRAINT app_versions_pkey PRIMARY KEY (version_id);


--
-- Name: app_versions app_versions_version_number_key; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.app_versions
    ADD CONSTRAINT app_versions_version_number_key UNIQUE (version_number);


--
-- Name: error_logs error_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_pkey PRIMARY KEY (error_id);


--
-- Name: function_usage_stats function_usage_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.function_usage_stats
    ADD CONSTRAINT function_usage_stats_pkey PRIMARY KEY (stat_id);


--
-- Name: installations installations_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.installations
    ADD CONSTRAINT installations_pkey PRIMARY KEY (installation_id);


--
-- Name: ldm_active_sessions ldm_active_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_sessions
    ADD CONSTRAINT ldm_active_sessions_pkey PRIMARY KEY (id);


--
-- Name: ldm_active_tms ldm_active_tms_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_tms
    ADD CONSTRAINT ldm_active_tms_pkey PRIMARY KEY (id);


--
-- Name: ldm_backups ldm_backups_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_backups
    ADD CONSTRAINT ldm_backups_pkey PRIMARY KEY (id);


--
-- Name: ldm_edit_history ldm_edit_history_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_edit_history
    ADD CONSTRAINT ldm_edit_history_pkey PRIMARY KEY (id);


--
-- Name: ldm_files ldm_files_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_files
    ADD CONSTRAINT ldm_files_pkey PRIMARY KEY (id);


--
-- Name: ldm_folders ldm_folders_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_folders
    ADD CONSTRAINT ldm_folders_pkey PRIMARY KEY (id);


--
-- Name: ldm_platforms ldm_platforms_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_platforms
    ADD CONSTRAINT ldm_platforms_pkey PRIMARY KEY (id);


--
-- Name: ldm_projects ldm_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_projects
    ADD CONSTRAINT ldm_projects_pkey PRIMARY KEY (id);


--
-- Name: ldm_qa_results ldm_qa_results_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_qa_results
    ADD CONSTRAINT ldm_qa_results_pkey PRIMARY KEY (id);


--
-- Name: ldm_resource_access ldm_resource_access_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access
    ADD CONSTRAINT ldm_resource_access_pkey PRIMARY KEY (id);


--
-- Name: ldm_rows ldm_rows_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_rows
    ADD CONSTRAINT ldm_rows_pkey PRIMARY KEY (id);


--
-- Name: ldm_tm_assignments ldm_tm_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments
    ADD CONSTRAINT ldm_tm_assignments_pkey PRIMARY KEY (id);


--
-- Name: ldm_tm_entries ldm_tm_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_entries
    ADD CONSTRAINT ldm_tm_entries_pkey PRIMARY KEY (id);


--
-- Name: ldm_tm_indexes ldm_tm_indexes_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_indexes
    ADD CONSTRAINT ldm_tm_indexes_pkey PRIMARY KEY (id);


--
-- Name: ldm_translation_memories ldm_translation_memories_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_translation_memories
    ADD CONSTRAINT ldm_translation_memories_pkey PRIMARY KEY (id);


--
-- Name: ldm_trash ldm_trash_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_trash
    ADD CONSTRAINT ldm_trash_pkey PRIMARY KEY (id);


--
-- Name: log_entries log_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.log_entries
    ADD CONSTRAINT log_entries_pkey PRIMARY KEY (log_id);


--
-- Name: performance_metrics performance_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.performance_metrics
    ADD CONSTRAINT performance_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: remote_logs remote_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.remote_logs
    ADD CONSTRAINT remote_logs_pkey PRIMARY KEY (log_id);


--
-- Name: remote_sessions remote_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.remote_sessions
    ADD CONSTRAINT remote_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id);


--
-- Name: telemetry_summary telemetry_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.telemetry_summary
    ADD CONSTRAINT telemetry_summary_pkey PRIMARY KEY (summary_id);


--
-- Name: tool_usage_stats tool_usage_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.tool_usage_stats
    ADD CONSTRAINT tool_usage_stats_pkey PRIMARY KEY (stat_id);


--
-- Name: update_history update_history_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.update_history
    ADD CONSTRAINT update_history_pkey PRIMARY KEY (update_id);


--
-- Name: ldm_files uq_ldm_file_name_project_folder; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_files
    ADD CONSTRAINT uq_ldm_file_name_project_folder UNIQUE (name, project_id, folder_id);


--
-- Name: ldm_folders uq_ldm_folder_name_project_parent; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_folders
    ADD CONSTRAINT uq_ldm_folder_name_project_parent UNIQUE (name, project_id, parent_id);


--
-- Name: ldm_platforms uq_ldm_platform_name_owner; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_platforms
    ADD CONSTRAINT uq_ldm_platform_name_owner UNIQUE (name, owner_id);


--
-- Name: ldm_projects uq_ldm_project_name_owner; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_projects
    ADD CONSTRAINT uq_ldm_project_name_owner UNIQUE (name, owner_id);


--
-- Name: ldm_resource_access uq_resource_access_platform_user; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access
    ADD CONSTRAINT uq_resource_access_platform_user UNIQUE (platform_id, user_id);


--
-- Name: ldm_resource_access uq_resource_access_project_user; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access
    ADD CONSTRAINT uq_resource_access_project_user UNIQUE (project_id, user_id);


--
-- Name: ldm_tm_assignments uq_tm_assignment_tm; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments
    ADD CONSTRAINT uq_tm_assignment_tm UNIQUE (tm_id);


--
-- Name: user_capabilities uq_user_capability; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_capabilities
    ADD CONSTRAINT uq_user_capability UNIQUE (user_id, capability_name);


--
-- Name: user_activity_summary user_activity_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_activity_summary
    ADD CONSTRAINT user_activity_summary_pkey PRIMARY KEY (summary_id);


--
-- Name: user_capabilities user_capabilities_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_capabilities
    ADD CONSTRAINT user_capabilities_pkey PRIMARY KEY (id);


--
-- Name: user_feedback user_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_pkey PRIMARY KEY (feedback_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: idx_active_status; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_active_status ON public.active_operations USING btree (status);


--
-- Name: idx_active_user_started; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_active_user_started ON public.active_operations USING btree (user_id, started_at);


--
-- Name: idx_activity_date_user; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_activity_date_user ON public.user_activity_summary USING btree (date, user_id);


--
-- Name: idx_error_timestamp_tool; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_error_timestamp_tool ON public.error_logs USING btree ("timestamp", tool_name);


--
-- Name: idx_func_stats_date_tool_func; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_func_stats_date_tool_func ON public.function_usage_stats USING btree (date, tool_name, function_name);


--
-- Name: idx_installation_active; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_installation_active ON public.installations USING btree (is_active);


--
-- Name: idx_installation_last_seen; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_installation_last_seen ON public.installations USING btree (last_seen);


--
-- Name: idx_ldm_active_tm_file; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_active_tm_file ON public.ldm_active_tms USING btree (file_id);


--
-- Name: idx_ldm_active_tm_project; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_active_tm_project ON public.ldm_active_tms USING btree (project_id);


--
-- Name: idx_ldm_active_tm_unique; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE UNIQUE INDEX idx_ldm_active_tm_unique ON public.ldm_active_tms USING btree (tm_id, project_id, file_id);


--
-- Name: idx_ldm_backup_created; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_backup_created ON public.ldm_backups USING btree (created_at);


--
-- Name: idx_ldm_backup_type; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_backup_type ON public.ldm_backups USING btree (backup_type);


--
-- Name: idx_ldm_file_project_folder; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_file_project_folder ON public.ldm_files USING btree (project_id, folder_id);


--
-- Name: idx_ldm_folder_project_parent; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_folder_project_parent ON public.ldm_folders USING btree (project_id, parent_id);


--
-- Name: idx_ldm_history_row_time; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_history_row_time ON public.ldm_edit_history USING btree (row_id, edited_at);


--
-- Name: idx_ldm_platform_owner; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_platform_owner ON public.ldm_platforms USING btree (owner_id);


--
-- Name: idx_ldm_project_owner; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_project_owner ON public.ldm_projects USING btree (owner_id);


--
-- Name: idx_ldm_row_file_rownum; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_row_file_rownum ON public.ldm_rows USING btree (file_id, row_num);


--
-- Name: idx_ldm_row_file_stringid; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_row_file_stringid ON public.ldm_rows USING btree (file_id, string_id);


--
-- Name: idx_ldm_row_status; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_row_status ON public.ldm_rows USING btree (status);


--
-- Name: idx_ldm_session_file; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_session_file ON public.ldm_active_sessions USING btree (file_id);


--
-- Name: idx_ldm_session_user; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_session_user ON public.ldm_active_sessions USING btree (user_id);


--
-- Name: idx_ldm_tm_entry_hash; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_entry_hash ON public.ldm_tm_entries USING btree (source_hash);


--
-- Name: idx_ldm_tm_entry_stringid; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_entry_stringid ON public.ldm_tm_entries USING btree (string_id);


--
-- Name: idx_ldm_tm_entry_tm; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_entry_tm ON public.ldm_tm_entries USING btree (tm_id);


--
-- Name: idx_ldm_tm_entry_tm_hash; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_entry_tm_hash ON public.ldm_tm_entries USING btree (tm_id, source_hash);


--
-- Name: idx_ldm_tm_entry_tm_hash_stringid; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_entry_tm_hash_stringid ON public.ldm_tm_entries USING btree (tm_id, source_hash, string_id);


--
-- Name: idx_ldm_tm_index_tm; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_index_tm ON public.ldm_tm_indexes USING btree (tm_id);


--
-- Name: idx_ldm_tm_index_type; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE UNIQUE INDEX idx_ldm_tm_index_type ON public.ldm_tm_indexes USING btree (tm_id, index_type);


--
-- Name: idx_ldm_tm_owner; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_owner ON public.ldm_translation_memories USING btree (owner_id);


--
-- Name: idx_ldm_tm_status; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_tm_status ON public.ldm_translation_memories USING btree (status);


--
-- Name: idx_ldm_trash_deleted_by; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_trash_deleted_by ON public.ldm_trash USING btree (deleted_by);


--
-- Name: idx_ldm_trash_expires; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_trash_expires ON public.ldm_trash USING btree (expires_at);


--
-- Name: idx_ldm_trash_type; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_ldm_trash_type ON public.ldm_trash USING btree (item_type);


--
-- Name: idx_log_timestamp_tool; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_log_timestamp_tool ON public.log_entries USING btree ("timestamp", tool_name);


--
-- Name: idx_log_user_timestamp; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_log_user_timestamp ON public.log_entries USING btree (user_id, "timestamp");


--
-- Name: idx_perf_timestamp_tool; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_perf_timestamp_tool ON public.performance_metrics USING btree ("timestamp", tool_name);


--
-- Name: idx_qa_result_file; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_qa_result_file ON public.ldm_qa_results USING btree (file_id);


--
-- Name: idx_qa_result_file_type; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_qa_result_file_type ON public.ldm_qa_results USING btree (file_id, check_type);


--
-- Name: idx_qa_result_row; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_qa_result_row ON public.ldm_qa_results USING btree (row_id);


--
-- Name: idx_qa_result_unique; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE UNIQUE INDEX idx_qa_result_unique ON public.ldm_qa_results USING btree (row_id, check_type, message);


--
-- Name: idx_qa_result_unresolved; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_qa_result_unresolved ON public.ldm_qa_results USING btree (file_id, resolved_at);


--
-- Name: idx_remote_log_installation_timestamp; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_remote_log_installation_timestamp ON public.remote_logs USING btree (installation_id, "timestamp");


--
-- Name: idx_remote_log_timestamp_level; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_remote_log_timestamp_level ON public.remote_logs USING btree ("timestamp", level);


--
-- Name: idx_remote_session_active; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_remote_session_active ON public.remote_sessions USING btree (is_active);


--
-- Name: idx_remote_session_installation_started; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_remote_session_installation_started ON public.remote_sessions USING btree (installation_id, started_at);


--
-- Name: idx_resource_access_platform; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_resource_access_platform ON public.ldm_resource_access USING btree (platform_id, user_id);


--
-- Name: idx_resource_access_project; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_resource_access_project ON public.ldm_resource_access USING btree (project_id, user_id);


--
-- Name: idx_telemetry_date_installation; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE UNIQUE INDEX idx_telemetry_date_installation ON public.telemetry_summary USING btree (date, installation_id);


--
-- Name: idx_tm_assignment_active; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_tm_assignment_active ON public.ldm_tm_assignments USING btree (is_active);


--
-- Name: idx_tm_assignment_folder; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_tm_assignment_folder ON public.ldm_tm_assignments USING btree (folder_id);


--
-- Name: idx_tm_assignment_platform; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_tm_assignment_platform ON public.ldm_tm_assignments USING btree (platform_id);


--
-- Name: idx_tm_assignment_project; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_tm_assignment_project ON public.ldm_tm_assignments USING btree (project_id);


--
-- Name: idx_tm_assignment_tm; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_tm_assignment_tm ON public.ldm_tm_assignments USING btree (tm_id);


--
-- Name: idx_tool_stats_date_tool; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX idx_tool_stats_date_tool ON public.tool_usage_stats USING btree (date, tool_name);


--
-- Name: ix_active_operations_function_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_active_operations_function_name ON public.active_operations USING btree (function_name);


--
-- Name: ix_active_operations_started_at; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_active_operations_started_at ON public.active_operations USING btree (started_at);


--
-- Name: ix_active_operations_status; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_active_operations_status ON public.active_operations USING btree (status);


--
-- Name: ix_active_operations_tool_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_active_operations_tool_name ON public.active_operations USING btree (tool_name);


--
-- Name: ix_active_operations_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_active_operations_user_id ON public.active_operations USING btree (user_id);


--
-- Name: ix_active_operations_username; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_active_operations_username ON public.active_operations USING btree (username);


--
-- Name: ix_error_logs_timestamp; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_error_logs_timestamp ON public.error_logs USING btree ("timestamp");


--
-- Name: ix_error_logs_tool_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_error_logs_tool_name ON public.error_logs USING btree (tool_name);


--
-- Name: ix_function_usage_stats_date; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_function_usage_stats_date ON public.function_usage_stats USING btree (date);


--
-- Name: ix_function_usage_stats_function_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_function_usage_stats_function_name ON public.function_usage_stats USING btree (function_name);


--
-- Name: ix_function_usage_stats_tool_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_function_usage_stats_tool_name ON public.function_usage_stats USING btree (tool_name);


--
-- Name: ix_installations_installation_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_installations_installation_name ON public.installations USING btree (installation_name);


--
-- Name: ix_installations_owner_email; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_installations_owner_email ON public.installations USING btree (owner_email);


--
-- Name: ix_ldm_active_sessions_file_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_active_sessions_file_id ON public.ldm_active_sessions USING btree (file_id);


--
-- Name: ix_ldm_active_sessions_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_active_sessions_user_id ON public.ldm_active_sessions USING btree (user_id);


--
-- Name: ix_ldm_active_tms_file_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_active_tms_file_id ON public.ldm_active_tms USING btree (file_id);


--
-- Name: ix_ldm_active_tms_project_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_active_tms_project_id ON public.ldm_active_tms USING btree (project_id);


--
-- Name: ix_ldm_active_tms_tm_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_active_tms_tm_id ON public.ldm_active_tms USING btree (tm_id);


--
-- Name: ix_ldm_edit_history_edited_at; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_edit_history_edited_at ON public.ldm_edit_history USING btree (edited_at);


--
-- Name: ix_ldm_edit_history_row_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_edit_history_row_id ON public.ldm_edit_history USING btree (row_id);


--
-- Name: ix_ldm_files_folder_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_files_folder_id ON public.ldm_files USING btree (folder_id);


--
-- Name: ix_ldm_files_project_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_files_project_id ON public.ldm_files USING btree (project_id);


--
-- Name: ix_ldm_folders_parent_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_folders_parent_id ON public.ldm_folders USING btree (parent_id);


--
-- Name: ix_ldm_folders_project_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_folders_project_id ON public.ldm_folders USING btree (project_id);


--
-- Name: ix_ldm_platforms_owner_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_platforms_owner_id ON public.ldm_platforms USING btree (owner_id);


--
-- Name: ix_ldm_projects_owner_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_projects_owner_id ON public.ldm_projects USING btree (owner_id);


--
-- Name: ix_ldm_qa_results_file_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_qa_results_file_id ON public.ldm_qa_results USING btree (file_id);


--
-- Name: ix_ldm_qa_results_row_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_qa_results_row_id ON public.ldm_qa_results USING btree (row_id);


--
-- Name: ix_ldm_resource_access_platform_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_resource_access_platform_id ON public.ldm_resource_access USING btree (platform_id);


--
-- Name: ix_ldm_resource_access_project_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_resource_access_project_id ON public.ldm_resource_access USING btree (project_id);


--
-- Name: ix_ldm_resource_access_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_resource_access_user_id ON public.ldm_resource_access USING btree (user_id);


--
-- Name: ix_ldm_rows_file_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_rows_file_id ON public.ldm_rows USING btree (file_id);


--
-- Name: ix_ldm_rows_string_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_rows_string_id ON public.ldm_rows USING btree (string_id);


--
-- Name: ix_ldm_tm_assignments_folder_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_tm_assignments_folder_id ON public.ldm_tm_assignments USING btree (folder_id);


--
-- Name: ix_ldm_tm_assignments_platform_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_tm_assignments_platform_id ON public.ldm_tm_assignments USING btree (platform_id);


--
-- Name: ix_ldm_tm_assignments_project_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_tm_assignments_project_id ON public.ldm_tm_assignments USING btree (project_id);


--
-- Name: ix_ldm_tm_assignments_tm_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_tm_assignments_tm_id ON public.ldm_tm_assignments USING btree (tm_id);


--
-- Name: ix_ldm_tm_entries_source_hash; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_tm_entries_source_hash ON public.ldm_tm_entries USING btree (source_hash);


--
-- Name: ix_ldm_tm_entries_tm_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_tm_entries_tm_id ON public.ldm_tm_entries USING btree (tm_id);


--
-- Name: ix_ldm_tm_indexes_tm_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_tm_indexes_tm_id ON public.ldm_tm_indexes USING btree (tm_id);


--
-- Name: ix_ldm_translation_memories_owner_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_translation_memories_owner_id ON public.ldm_translation_memories USING btree (owner_id);


--
-- Name: ix_ldm_trash_deleted_at; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_ldm_trash_deleted_at ON public.ldm_trash USING btree (deleted_at);


--
-- Name: ix_log_entries_function_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_log_entries_function_name ON public.log_entries USING btree (function_name);


--
-- Name: ix_log_entries_machine_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_log_entries_machine_id ON public.log_entries USING btree (machine_id);


--
-- Name: ix_log_entries_timestamp; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_log_entries_timestamp ON public.log_entries USING btree ("timestamp");


--
-- Name: ix_log_entries_tool_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_log_entries_tool_name ON public.log_entries USING btree (tool_name);


--
-- Name: ix_log_entries_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_log_entries_user_id ON public.log_entries USING btree (user_id);


--
-- Name: ix_log_entries_username; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_log_entries_username ON public.log_entries USING btree (username);


--
-- Name: ix_performance_metrics_timestamp; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_performance_metrics_timestamp ON public.performance_metrics USING btree ("timestamp");


--
-- Name: ix_performance_metrics_tool_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_performance_metrics_tool_name ON public.performance_metrics USING btree (tool_name);


--
-- Name: ix_remote_logs_installation_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_remote_logs_installation_id ON public.remote_logs USING btree (installation_id);


--
-- Name: ix_remote_logs_level; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_remote_logs_level ON public.remote_logs USING btree (level);


--
-- Name: ix_remote_logs_received_at; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_remote_logs_received_at ON public.remote_logs USING btree (received_at);


--
-- Name: ix_remote_logs_source; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_remote_logs_source ON public.remote_logs USING btree (source);


--
-- Name: ix_remote_logs_timestamp; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_remote_logs_timestamp ON public.remote_logs USING btree ("timestamp");


--
-- Name: ix_remote_sessions_installation_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_remote_sessions_installation_id ON public.remote_sessions USING btree (installation_id);


--
-- Name: ix_remote_sessions_started_at; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_remote_sessions_started_at ON public.remote_sessions USING btree (started_at);


--
-- Name: ix_sessions_machine_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_sessions_machine_id ON public.sessions USING btree (machine_id);


--
-- Name: ix_sessions_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_sessions_user_id ON public.sessions USING btree (user_id);


--
-- Name: ix_telemetry_summary_date; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_telemetry_summary_date ON public.telemetry_summary USING btree (date);


--
-- Name: ix_telemetry_summary_installation_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_telemetry_summary_installation_id ON public.telemetry_summary USING btree (installation_id);


--
-- Name: ix_tool_usage_stats_date; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_tool_usage_stats_date ON public.tool_usage_stats USING btree (date);


--
-- Name: ix_tool_usage_stats_tool_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_tool_usage_stats_tool_name ON public.tool_usage_stats USING btree (tool_name);


--
-- Name: ix_update_history_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_update_history_user_id ON public.update_history USING btree (user_id);


--
-- Name: ix_user_activity_summary_date; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_user_activity_summary_date ON public.user_activity_summary USING btree (date);


--
-- Name: ix_user_activity_summary_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_user_activity_summary_user_id ON public.user_activity_summary USING btree (user_id);


--
-- Name: ix_user_capabilities_capability_name; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_user_capabilities_capability_name ON public.user_capabilities USING btree (capability_name);


--
-- Name: ix_user_capabilities_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_user_capabilities_user_id ON public.user_capabilities USING btree (user_id);


--
-- Name: ix_user_feedback_user_id; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_user_feedback_user_id ON public.user_feedback USING btree (user_id);


--
-- Name: ix_users_department; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_users_department ON public.users USING btree (department);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_language; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_users_language ON public.users USING btree (language);


--
-- Name: ix_users_team; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE INDEX ix_users_team ON public.users USING btree (team);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: localization_admin
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: active_operations active_operations_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.active_operations
    ADD CONSTRAINT active_operations_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(session_id) ON DELETE SET NULL;


--
-- Name: active_operations active_operations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.active_operations
    ADD CONSTRAINT active_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: error_logs error_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: ldm_active_sessions ldm_active_sessions_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_sessions
    ADD CONSTRAINT ldm_active_sessions_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.ldm_files(id) ON DELETE CASCADE;


--
-- Name: ldm_active_sessions ldm_active_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_sessions
    ADD CONSTRAINT ldm_active_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: ldm_active_tms ldm_active_tms_activated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_tms
    ADD CONSTRAINT ldm_active_tms_activated_by_fkey FOREIGN KEY (activated_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_active_tms ldm_active_tms_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_tms
    ADD CONSTRAINT ldm_active_tms_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.ldm_files(id) ON DELETE CASCADE;


--
-- Name: ldm_active_tms ldm_active_tms_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_tms
    ADD CONSTRAINT ldm_active_tms_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.ldm_projects(id) ON DELETE CASCADE;


--
-- Name: ldm_active_tms ldm_active_tms_tm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_active_tms
    ADD CONSTRAINT ldm_active_tms_tm_id_fkey FOREIGN KEY (tm_id) REFERENCES public.ldm_translation_memories(id) ON DELETE CASCADE;


--
-- Name: ldm_backups ldm_backups_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_backups
    ADD CONSTRAINT ldm_backups_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_edit_history ldm_edit_history_row_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_edit_history
    ADD CONSTRAINT ldm_edit_history_row_id_fkey FOREIGN KEY (row_id) REFERENCES public.ldm_rows(id) ON DELETE CASCADE;


--
-- Name: ldm_edit_history ldm_edit_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_edit_history
    ADD CONSTRAINT ldm_edit_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_files ldm_files_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_files
    ADD CONSTRAINT ldm_files_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_files ldm_files_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_files
    ADD CONSTRAINT ldm_files_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.ldm_folders(id) ON DELETE SET NULL;


--
-- Name: ldm_files ldm_files_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_files
    ADD CONSTRAINT ldm_files_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.ldm_projects(id) ON DELETE CASCADE;


--
-- Name: ldm_folders ldm_folders_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_folders
    ADD CONSTRAINT ldm_folders_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.ldm_folders(id) ON DELETE CASCADE;


--
-- Name: ldm_folders ldm_folders_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_folders
    ADD CONSTRAINT ldm_folders_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.ldm_projects(id) ON DELETE CASCADE;


--
-- Name: ldm_platforms ldm_platforms_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_platforms
    ADD CONSTRAINT ldm_platforms_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: ldm_projects ldm_projects_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_projects
    ADD CONSTRAINT ldm_projects_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: ldm_qa_results ldm_qa_results_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_qa_results
    ADD CONSTRAINT ldm_qa_results_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.ldm_files(id) ON DELETE CASCADE;


--
-- Name: ldm_qa_results ldm_qa_results_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_qa_results
    ADD CONSTRAINT ldm_qa_results_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_qa_results ldm_qa_results_row_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_qa_results
    ADD CONSTRAINT ldm_qa_results_row_id_fkey FOREIGN KEY (row_id) REFERENCES public.ldm_rows(id) ON DELETE CASCADE;


--
-- Name: ldm_resource_access ldm_resource_access_granted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access
    ADD CONSTRAINT ldm_resource_access_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_resource_access ldm_resource_access_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access
    ADD CONSTRAINT ldm_resource_access_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.ldm_platforms(id) ON DELETE CASCADE;


--
-- Name: ldm_resource_access ldm_resource_access_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access
    ADD CONSTRAINT ldm_resource_access_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.ldm_projects(id) ON DELETE CASCADE;


--
-- Name: ldm_resource_access ldm_resource_access_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_resource_access
    ADD CONSTRAINT ldm_resource_access_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: ldm_rows ldm_rows_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_rows
    ADD CONSTRAINT ldm_rows_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.ldm_files(id) ON DELETE CASCADE;


--
-- Name: ldm_rows ldm_rows_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_rows
    ADD CONSTRAINT ldm_rows_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_tm_assignments ldm_tm_assignments_assigned_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments
    ADD CONSTRAINT ldm_tm_assignments_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ldm_tm_assignments ldm_tm_assignments_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments
    ADD CONSTRAINT ldm_tm_assignments_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.ldm_folders(id) ON DELETE SET NULL;


--
-- Name: ldm_tm_assignments ldm_tm_assignments_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments
    ADD CONSTRAINT ldm_tm_assignments_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.ldm_platforms(id) ON DELETE SET NULL;


--
-- Name: ldm_tm_assignments ldm_tm_assignments_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments
    ADD CONSTRAINT ldm_tm_assignments_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.ldm_projects(id) ON DELETE SET NULL;


--
-- Name: ldm_tm_assignments ldm_tm_assignments_tm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_assignments
    ADD CONSTRAINT ldm_tm_assignments_tm_id_fkey FOREIGN KEY (tm_id) REFERENCES public.ldm_translation_memories(id) ON DELETE CASCADE;


--
-- Name: ldm_tm_entries ldm_tm_entries_tm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_entries
    ADD CONSTRAINT ldm_tm_entries_tm_id_fkey FOREIGN KEY (tm_id) REFERENCES public.ldm_translation_memories(id) ON DELETE CASCADE;


--
-- Name: ldm_tm_indexes ldm_tm_indexes_tm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_tm_indexes
    ADD CONSTRAINT ldm_tm_indexes_tm_id_fkey FOREIGN KEY (tm_id) REFERENCES public.ldm_translation_memories(id) ON DELETE CASCADE;


--
-- Name: ldm_translation_memories ldm_translation_memories_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_translation_memories
    ADD CONSTRAINT ldm_translation_memories_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: ldm_trash ldm_trash_deleted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.ldm_trash
    ADD CONSTRAINT ldm_trash_deleted_by_fkey FOREIGN KEY (deleted_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: log_entries log_entries_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.log_entries
    ADD CONSTRAINT log_entries_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(session_id) ON DELETE SET NULL;


--
-- Name: log_entries log_entries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.log_entries
    ADD CONSTRAINT log_entries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: remote_logs remote_logs_installation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.remote_logs
    ADD CONSTRAINT remote_logs_installation_id_fkey FOREIGN KEY (installation_id) REFERENCES public.installations(installation_id) ON DELETE CASCADE;


--
-- Name: remote_sessions remote_sessions_installation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.remote_sessions
    ADD CONSTRAINT remote_sessions_installation_id_fkey FOREIGN KEY (installation_id) REFERENCES public.installations(installation_id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: telemetry_summary telemetry_summary_installation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.telemetry_summary
    ADD CONSTRAINT telemetry_summary_installation_id_fkey FOREIGN KEY (installation_id) REFERENCES public.installations(installation_id) ON DELETE CASCADE;


--
-- Name: update_history update_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.update_history
    ADD CONSTRAINT update_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_activity_summary user_activity_summary_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_activity_summary
    ADD CONSTRAINT user_activity_summary_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_capabilities user_capabilities_granted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_capabilities
    ADD CONSTRAINT user_capabilities_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: user_capabilities user_capabilities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_capabilities
    ADD CONSTRAINT user_capabilities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_feedback user_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: users users_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: localization_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict a2SvsagNLhzQmJk7vWaCEGyqa0raRkSOO2mrThEo82RPSS8rEWSYXYbzD2O6IHM

