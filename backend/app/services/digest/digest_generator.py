from datetime import datetime, timezone
from typing import List, Optional
from app.schemas.digest import DigestJobItem


class DigestGenerator:
    """Renders responsive HTML and multi-part text email templates for daily digests."""

    def render_digest_html(
        self,
        recipient_name: str,
        date_str: str,
        total_jobs_evaluated: int,
        top_matches: List[DigestJobItem],
        interview_count: int = 0,
    ) -> str:
        """Renders an elegant, modern email digest compatible with major email clients."""
        job_cards_html = ""
        for job in top_matches:
            salary_badge = (
                f'<span style="background-color: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-left: 8px;">{job.salary_formatted}</span>'
                if job.salary_formatted
                else ""
            )

            # Score color styling
            score_bg = "#10b981" if job.match_score >= 80 else "#3b82f6" if job.match_score >= 65 else "#6b7280"

            skills_html = ""
            if job.matched_skills:
                skill_pills = "".join(
                    f'<span style="display: inline-block; background-color: #f1f5f9; color: #334155; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 5px; margin-bottom: 5px;">{s}</span>'
                    for s in job.matched_skills[:6]
                )
                skills_html = f'<div style="margin-top: 8px;">{skill_pills}</div>'

            apply_button = ""
            if job.job_url:
                apply_button = f'''
                <a href="{job.job_url}" target="_blank" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; margin-top: 10px;">
                    View & Apply &rarr;
                </a>
                '''

            job_cards_html += f"""
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex-grow: 1;">
                        <h3 style="margin: 0 0 4px 0; font-size: 16px; color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                            {job.title}
                        </h3>
                        <p style="margin: 0; font-size: 14px; color: #475569; font-weight: 500;">
                            {job.company_name} &bull; <span style="color: #64748b;">{job.location or 'Location Not Specified'}</span>
                            <span style="background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px;">{job.work_mode}</span>
                            {salary_badge}
                        </p>
                    </div>
                    <div style="background-color: {score_bg}; color: #ffffff; padding: 6px 10px; border-radius: 6px; font-size: 13px; font-weight: bold; text-align: center; white-space: nowrap;">
                        {round(job.match_score)}% Match
                    </div>
                </div>
                {skills_html}
                {apply_button}
            </div>
            """

        if not job_cards_html:
            job_cards_html = """
            <div style="background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 24px; text-align: center; color: #64748b;">
                <p style="margin: 0; font-size: 14px;">No new high-match positions discovered in the last 24 hours.</p>
                <p style="margin: 6px 0 0 0; font-size: 12px; color: #94a3b8;">We are continuously monitoring your incoming emails for opportunities.</p>
            </div>
            """

        interview_banner = ""
        if interview_count > 0:
            interview_banner = f"""
            <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
                <strong style="color: #1e40af; font-size: 14px;">Action Required:</strong>
                <span style="color: #1e3a8a; font-size: 14px; margin-left: 4px;">You have {interview_count} active interview update(s) or invitations pending review!</span>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily AI Job Digest - {date_str}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9; padding: 24px 0;">
        <tr>
            <td align="center">
                <table width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 32px 28px; text-align: left;">
                            <div style="color: #38bdf8; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px;">AI Job Intelligence</div>
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">Daily Intelligence Digest</h1>
                            <p style="color: #94a3b8; margin: 6px 0 0 0; font-size: 14px;">Prepared for {recipient_name} &bull; {date_str}</p>
                        </td>
                    </tr>

                    <!-- Metrics bar -->
                    <tr>
                        <td style="padding: 20px 28px; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td width="50%" align="center" style="border-right: 1px solid #e2e8f0;">
                                        <div style="font-size: 24px; font-weight: 700; color: #0f172a;">{total_jobs_evaluated}</div>
                                        <div style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Jobs Evaluated</div>
                                    </td>
                                    <td width="50%" align="center">
                                        <div style="font-size: 24px; font-weight: 700; color: #10b981;">{len(top_matches)}</div>
                                        <div style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Top Matches</div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Content Body -->
                    <tr>
                        <td style="padding: 28px;">
                            {interview_banner}
                            <h2 style="margin: 0 0 16px 0; font-size: 18px; color: #0f172a;">Top Matching Opportunities</h2>
                            {job_cards_html}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 28px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; color: #94a3b8; font-size: 12px;">
                            <p style="margin: 0 0 8px 0;">This email was automatically generated by your AI Job Email Intelligence System.</p>
                            <p style="margin: 0;">
                                <a href="http://localhost:5173/settings" style="color: #64748b; text-decoration: underline;">Manage Digest Settings</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def render_digest_text(
        self,
        recipient_name: str,
        date_str: str,
        total_jobs_evaluated: int,
        top_matches: List[DigestJobItem],
        interview_count: int = 0,
    ) -> str:
        """Renders plain text equivalent for multi-part email compliance."""
        lines = [
            f"AI JOB INTELLIGENCE - DAILY DIGEST ({date_str})",
            f"Hello {recipient_name},",
            "",
            f"Summary: {total_jobs_evaluated} jobs evaluated, {len(top_matches)} top matches found.",
        ]

        if interview_count > 0:
            lines.append(f"ACTION REQUIRED: You have {interview_count} active interview update(s) pending!")

        lines.extend(["", "--- TOP MATCHING OPPORTUNITIES ---", ""])

        if not top_matches:
            lines.append("No new high-match positions discovered in the last 24 hours.")
        else:
            for i, job in enumerate(top_matches, 1):
                salary_part = f" | {job.salary_formatted}" if job.salary_formatted else ""
                lines.append(f"{i}. {job.title} at {job.company_name} [{round(job.match_score)}% Match]")
                lines.append(f"   Location: {job.location or 'N/A'} ({job.work_mode}){salary_part}")
                if job.matched_skills:
                    lines.append(f"   Key Skills: {', '.join(job.matched_skills[:5])}")
                if job.job_url:
                    lines.append(f"   Apply: {job.job_url}")
                lines.append("")

        lines.extend([
            "---",
            "Manage your digest preferences: http://localhost:5173/settings",
            "AI Job Email Intelligence System",
        ])
        return "\n".join(lines)


digest_generator = DigestGenerator()
