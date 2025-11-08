"""
Admin Dashboard

Gradio interface for administrators to view statistics, manage users, and monitor logs.
"""

import gradio as gr
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from loguru import logger

from server.database.db_setup import get_session_maker, create_database_engine
from server.database.models import (
    User, Session, LogEntry, ToolUsageStats, FunctionUsageStats,
    ErrorLog, Announcement
)
from server import config
from sqlalchemy import func, desc


# ============================================================================
# Database Connection
# ============================================================================

def get_db_session():
    """Get database session for dashboard queries."""
    use_postgres = config.DATABASE_TYPE == "postgresql"
    engine = create_database_engine(use_postgres=use_postgres, echo=False)
    session_maker = get_session_maker(engine)
    return session_maker()


# ============================================================================
# Statistics Functions
# ============================================================================

def get_dashboard_overview():
    """
    Get overview statistics for dashboard.

    Returns:
        HTML formatted overview statistics.
    """
    db = get_db_session()
    try:
        # Total users
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()

        # Total operations
        total_ops = db.query(LogEntry).count()

        # Operations today
        today = datetime.utcnow().date()
        ops_today = db.query(LogEntry).filter(
            func.date(LogEntry.timestamp) == today
        ).count()

        # Active sessions
        active_sessions = db.query(Session).filter(Session.is_active == True).count()

        # Success rate
        success_count = db.query(LogEntry).filter(LogEntry.status == "success").count()
        success_rate = (success_count / total_ops * 100) if total_ops > 0 else 0

        # Average operation duration
        avg_duration = db.query(func.avg(LogEntry.duration_seconds)).scalar() or 0.0

        # Recent errors
        errors_today = db.query(ErrorLog).filter(
            func.date(ErrorLog.timestamp) == today
        ).count()

        html = f"""
        <div style="padding: 20px; background: #f5f5f5; border-radius: 10px;">
            <h2 style="margin-top: 0;">📊 Dashboard Overview</h2>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px;">
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0; color: #666; font-size: 14px;">Total Users</h3>
                    <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #333;">{total_users}</p>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #999;">({active_users} active)</p>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0; color: #666; font-size: 14px;">Total Operations</h3>
                    <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #333;">{total_ops:,}</p>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #999;">{ops_today} today</p>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0; color: #666; font-size: 14px;">Success Rate</h3>
                    <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #28a745;">{success_rate:.1f}%</p>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #999;">Avg: {avg_duration:.2f}s</p>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0; color: #666; font-size: 14px;">Active Sessions</h3>
                    <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #007bff;">{active_sessions}</p>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: {'#dc3545' if errors_today > 0 else '#999'};">{errors_today} errors today</p>
                </div>
            </div>
        </div>
        """

        return html

    except Exception as e:
        logger.exception(f"Error getting dashboard overview: {e}")
        return f"<p style='color: red;'>Error loading overview: {str(e)}</p>"
    finally:
        db.close()


def get_tool_usage_stats():
    """
    Get tool usage statistics.

    Returns:
        DataFrame with tool usage data.
    """
    db = get_db_session()
    try:
        stats = db.query(
            LogEntry.tool_name,
            func.count(LogEntry.log_id).label("total_uses"),
            func.count(func.distinct(LogEntry.user_id)).label("unique_users"),
            func.avg(LogEntry.duration_seconds).label("avg_duration"),
            func.sum(
                func.cast(LogEntry.status == "success", db.bind.dialect.type_descriptor(func.Integer()))
            ).label("success_count")
        ).group_by(
            LogEntry.tool_name
        ).order_by(
            desc("total_uses")
        ).all()

        data = []
        for stat in stats:
            success_rate = (stat.success_count / stat.total_uses * 100) if stat.total_uses > 0 else 0
            data.append({
                "Tool": stat.tool_name,
                "Total Uses": stat.total_uses,
                "Unique Users": stat.unique_users,
                "Avg Duration (s)": round(stat.avg_duration, 2),
                "Success Rate (%)": round(success_rate, 1)
            })

        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=["Tool", "Total Uses", "Unique Users", "Avg Duration (s)", "Success Rate (%)"])

    except Exception as e:
        logger.exception(f"Error getting tool stats: {e}")
        return pd.DataFrame(columns=["Tool", "Total Uses", "Unique Users", "Avg Duration (s)", "Success Rate (%)"])
    finally:
        db.close()


def get_recent_logs(limit: int = 50, tool_filter: Optional[str] = None):
    """
    Get recent log entries.

    Args:
        limit: Maximum number of logs to retrieve.
        tool_filter: Optional tool name filter.

    Returns:
        DataFrame with recent logs.
    """
    db = get_db_session()
    try:
        query = db.query(LogEntry)

        if tool_filter and tool_filter != "All":
            query = query.filter(LogEntry.tool_name == tool_filter)

        logs = query.order_by(desc(LogEntry.timestamp)).limit(limit).all()

        data = []
        for log in logs:
            data.append({
                "Timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "User": log.username,
                "Tool": log.tool_name,
                "Function": log.function_name,
                "Duration (s)": round(log.duration_seconds, 2),
                "Status": log.status
            })

        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=["Timestamp", "User", "Tool", "Function", "Duration (s)", "Status"])

    except Exception as e:
        logger.exception(f"Error getting recent logs: {e}")
        return pd.DataFrame(columns=["Timestamp", "User", "Tool", "Function", "Duration (s)", "Status"])
    finally:
        db.close()


def get_user_list():
    """
    Get list of all users.

    Returns:
        DataFrame with user data.
    """
    db = get_db_session()
    try:
        users = db.query(User).all()

        data = []
        for user in users:
            # Count user's operations
            op_count = db.query(LogEntry).filter(LogEntry.user_id == user.user_id).count()

            data.append({
                "ID": user.user_id,
                "Username": user.username,
                "Email": user.email or "N/A",
                "Department": user.department or "N/A",
                "Role": user.role,
                "Active": "✓" if user.is_active else "✗",
                "Operations": op_count,
                "Last Login": user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
            })

        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=["ID", "Username", "Email", "Department", "Role", "Active", "Operations", "Last Login"])

    except Exception as e:
        logger.exception(f"Error getting user list: {e}")
        return pd.DataFrame(columns=["ID", "Username", "Email", "Department", "Role", "Active", "Operations", "Last Login"])
    finally:
        db.close()


def get_recent_errors(limit: int = 20):
    """
    Get recent error logs.

    Args:
        limit: Maximum number of errors to retrieve.

    Returns:
        DataFrame with error data.
    """
    db = get_db_session()
    try:
        errors = db.query(ErrorLog).order_by(desc(ErrorLog.timestamp)).limit(limit).all()

        data = []
        for error in errors:
            # Get username
            user = db.query(User).filter(User.user_id == error.user_id).first()
            username = user.username if user else "Unknown"

            data.append({
                "Timestamp": error.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "User": username,
                "Tool": error.tool_name,
                "Function": error.function_name,
                "Error Type": error.error_type,
                "Message": error.error_message[:100] + "..." if len(error.error_message) > 100 else error.error_message
            })

        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=["Timestamp", "User", "Tool", "Function", "Error Type", "Message"])

    except Exception as e:
        logger.exception(f"Error getting recent errors: {e}")
        return pd.DataFrame(columns=["Timestamp", "User", "Tool", "Function", "Error Type", "Message"])
    finally:
        db.close()


# ============================================================================
# Gradio Interface
# ============================================================================

def create_admin_dashboard():
    """
    Create the admin dashboard Gradio interface.

    Returns:
        Gradio Blocks interface.
    """
    with gr.Blocks(
        title="LocalizationTools Admin Dashboard",
        theme=gr.themes.Soft()
    ) as dashboard:

        gr.Markdown("# 🎛️ LocalizationTools Admin Dashboard")
        gr.Markdown(f"*Server: {config.APP_NAME} v{config.APP_VERSION}*")

        with gr.Tabs():

            # Overview Tab
            with gr.Tab("📊 Overview"):
                overview_html = gr.HTML(get_dashboard_overview())

                gr.Markdown("### Tool Usage Statistics")
                tool_stats_df = gr.Dataframe(
                    value=get_tool_usage_stats(),
                    interactive=False
                )

                refresh_overview_btn = gr.Button("🔄 Refresh Overview", variant="primary")
                refresh_overview_btn.click(
                    fn=lambda: (get_dashboard_overview(), get_tool_usage_stats()),
                    outputs=[overview_html, tool_stats_df]
                )

            # Logs Tab
            with gr.Tab("📋 Logs"):
                gr.Markdown("### Recent Activity Logs")

                with gr.Row():
                    log_limit = gr.Slider(
                        minimum=10, maximum=200, value=50, step=10,
                        label="Number of logs to display"
                    )
                    tool_filter = gr.Dropdown(
                        choices=["All"], value="All",
                        label="Filter by tool"
                    )

                logs_df = gr.Dataframe(
                    value=get_recent_logs(50),
                    interactive=False
                )

                refresh_logs_btn = gr.Button("🔄 Refresh Logs")
                refresh_logs_btn.click(
                    fn=lambda limit, filter: get_recent_logs(limit, filter),
                    inputs=[log_limit, tool_filter],
                    outputs=logs_df
                )

            # Users Tab
            with gr.Tab("👥 Users"):
                gr.Markdown("### User Management")

                users_df = gr.Dataframe(
                    value=get_user_list(),
                    interactive=False
                )

                refresh_users_btn = gr.Button("🔄 Refresh Users")
                refresh_users_btn.click(
                    fn=get_user_list,
                    outputs=users_df
                )

            # Errors Tab
            with gr.Tab("⚠️ Errors"):
                gr.Markdown("### Recent Errors")

                error_limit = gr.Slider(
                    minimum=5, maximum=100, value=20, step=5,
                    label="Number of errors to display"
                )

                errors_df = gr.Dataframe(
                    value=get_recent_errors(20),
                    interactive=False
                )

                refresh_errors_btn = gr.Button("🔄 Refresh Errors")
                refresh_errors_btn.click(
                    fn=get_recent_errors,
                    inputs=error_limit,
                    outputs=errors_df
                )

            # Settings Tab
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("### Server Settings")

                settings_info = f"""
                **Application**: {config.APP_NAME}
                **Version**: {config.APP_VERSION}
                **Database**: {config.DATABASE_TYPE.upper()}
                **Server**: {config.SERVER_HOST}:{config.SERVER_PORT}
                **Admin Port**: {config.ADMIN_DASHBOARD_PORT}
                **Debug Mode**: {'Enabled' if config.DEBUG else 'Disabled'}
                **API Docs**: {'Enabled' if config.ENABLE_DOCS else 'Disabled'}
                """

                gr.Markdown(settings_info)

        # Footer
        gr.Markdown("---")
        gr.Markdown(f"*Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*")

    return dashboard


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Admin Dashboard...")

    dashboard = create_admin_dashboard()

    dashboard.launch(
        server_name="0.0.0.0",
        server_port=config.ADMIN_DASHBOARD_PORT,
        share=False,
        show_error=True,
        quiet=False
    )
