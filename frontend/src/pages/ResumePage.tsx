import React, { useEffect, useState } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { api } from '../api/client';
import {
  Upload,
  Sparkles,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  GraduationCap,
  Trash2,
  ArrowRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ContactInfo {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
}

interface WorkExperienceItem {
  company: string;
  role: string;
  start_date?: string;
  end_date?: string;
  is_current?: boolean;
  duration_years?: number;
  description?: string;
  skills_used: string[];
}

interface EducationItem {
  institution: string;
  degree?: string;
  field_of_study?: string;
  graduation_year?: number;
  gpa?: string;
}

interface SkillItem {
  name: string;
  category?: string;
  years_experience?: number;
}

interface ParsedResumeData {
  contact_info?: ContactInfo;
  summary?: string;
  total_experience_years?: number;
  experience?: WorkExperienceItem[];
  education?: EducationItem[];
  skills?: SkillItem[];
  certifications?: string[];
}

interface StructuredResumeResponse {
  id: string;
  user_id: string;
  file_name: string;
  parsed_data: ParsedResumeData;
  skills_count: number;
  experience_count: number;
  education_count: number;
  total_experience_years?: number;
  created_at: string;
  updated_at: string;
}

export const ResumePage: React.FC = () => {
  const navigate = useNavigate();
  const [resume, setResume] = useState<StructuredResumeResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isParsing, setIsParsing] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const fetchResume = async () => {
    setIsLoading(true);
    try {
      const data = await api.get<StructuredResumeResponse>('/resumes/me/structured');
      setResume(data);
    } catch {
      // Fallback: Check if basic resume exists
      try {
        const basic = await api.get<{ id: string; file_name: string; total_experience_years?: number; parsed_summary?: string }>('/resumes/me');
        if (basic && basic.id) {
          setResume({
            id: basic.id,
            user_id: '',
            file_name: basic.file_name,
            parsed_data: {
              summary: basic.parsed_summary,
              total_experience_years: basic.total_experience_years,
              skills: [],
              experience: [],
              education: [],
            },
            skills_count: 0,
            experience_count: 0,
            education_count: 0,
            total_experience_years: basic.total_experience_years,
            created_at: '',
            updated_at: '',
          });
        } else {
          setResume(null);
        }
      } catch {
        setResume(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchResume();
  }, []);

  const handleFileUpload = async (fileToUpload: File) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', fileToUpload);

    try {
      await api.post('/resumes/upload', formData);
      setFile(null);
      // Auto trigger parse
      await api.post('/resumes/parse');
      await fetchResume();
      alert('Resume uploaded and structured successfully!');
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleParse = async () => {
    setIsParsing(true);
    try {
      await api.post('/resumes/parse');
      await fetchResume();
      alert('Resume re-parsed and candidate profile updated.');
    } catch (err: any) {
      alert(`Parsing failed: ${err.message}`);
    } finally {
      setIsParsing(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to remove your resume? All calculated match scores will be reset.')) {
      return;
    }
    setIsDeleting(true);
    try {
      await api.delete('/resumes/me');
      setResume(null);
      alert('Resume removed successfully.');
    } catch (err: any) {
      alert(`Failed to delete resume: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const parsed = resume?.parsed_data;
  const contact = parsed?.contact_info;

  return (
    <AppLayout title="Candidate Profile & Resume Intelligence">
      {isLoading ? (
        <Card style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading candidate profile and structured resume data...
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Top Header Card */}
          {resume && (
          <div
            style={{
              padding: '24px',
              borderRadius: 'var(--radius-lg)',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(15, 23, 42, 0.8) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Active Profile Document:</span>
                <Badge variant="primary">{resume.file_name}</Badge>
              </div>
              <h2 style={{ fontSize: '22px', fontWeight: 700, margin: '0 0 6px 0', color: 'var(--text-primary)' }}>
                {contact?.name || 'Candidate Profile'}
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', fontSize: '13px', color: 'var(--text-secondary)' }}>
                {contact?.email && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Mail size={14} color="var(--text-muted)" />
                    {contact.email}
                  </span>
                )}
                {contact?.phone && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Phone size={14} color="var(--text-muted)" />
                    {contact.phone}
                  </span>
                )}
                {contact?.location && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <MapPin size={14} color="var(--text-muted)" />
                    {contact.location}
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Button
                variant="outline"
                size="md"
                isLoading={isParsing}
                leftIcon={<Sparkles size={16} />}
                onClick={handleParse}
              >
                Re-parse
              </Button>
              <Button
                variant="primary"
                size="md"
                rightIcon={<ArrowRight size={16} />}
                onClick={() => navigate('/matches')}
              >
                View Matches
              </Button>
              <Button
                variant="danger"
                size="md"
                isLoading={isDeleting}
                onClick={handleDelete}
                title="Delete active resume"
              >
                <Trash2 size={16} />
              </Button>
            </div>
          </div>
        )}

        {/* Upload or Update Zone */}
        <div style={{ display: 'grid', gridTemplateColumns: resume ? '1fr 2fr' : '1fr', gap: '24px' }}>
          {/* Upload Widget */}
          <Card style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '17px', margin: '0 0 8px 0', fontWeight: 600 }}>
              {resume ? 'Replace Resume' : 'Upload Candidate Resume'}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '18px', lineHeight: 1.45 }}>
              Upload your latest resume (PDF, Markdown, or TXT). Text is extracted securely for ATS scoring and skills gap modeling.
            </p>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  setFile(e.dataTransfer.files[0]);
                  handleFileUpload(e.dataTransfer.files[0]);
                }
              }}
              style={{
                border: isDragging ? '2px dashed var(--accent-primary)' : '2px dashed var(--border-medium)',
                borderRadius: 'var(--radius-lg)',
                padding: '32px 16px',
                textAlign: 'center',
                backgroundColor: isDragging ? 'rgba(99, 102, 241, 0.08)' : 'rgba(255, 255, 255, 0.01)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                marginBottom: '16px',
              }}
              onClick={() => document.getElementById('resume-file-input')?.click()}
            >
              <input
                id="resume-file-input"
                type="file"
                accept=".pdf,.txt,.md,.text,.markdown"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setFile(e.target.files[0]);
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />
              <Upload size={32} style={{ color: 'var(--accent-primary)', margin: '0 auto 10px auto' }} />
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                {file ? file.name : 'Click or drop resume file here'}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                PDF, Markdown, or Plain Text up to 10MB
              </div>
            </div>

            {isUploading && (
              <div style={{ textAlign: 'center', padding: '12px 0', fontSize: '13px', color: 'var(--accent-primary)' }}>
                Extracting and parsing resume structure...
              </div>
            )}
          </Card>

          {/* Profile Overview (Summary & Experience) */}
          {resume && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Metrics Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
                <Card style={{ padding: '16px' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Total Experience
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '4px' }}>
                    {parsed?.total_experience_years !== undefined
                      ? `${parsed.total_experience_years} Years`
                      : 'Not specified'}
                  </div>
                </Card>

                <Card style={{ padding: '16px' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Extracted Skills
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--success)', marginTop: '4px' }}>
                    {resume.skills_count || (parsed?.skills ? parsed.skills.length : 0)}
                  </div>
                </Card>

                <Card style={{ padding: '16px' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Career Roles
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--accent-secondary)', marginTop: '4px' }}>
                    {resume.experience_count || (parsed?.experience ? parsed.experience.length : 0)}
                  </div>
                </Card>
              </div>

              {/* Executive Summary */}
              {parsed?.summary && (
                <Card style={{ padding: '20px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 8px 0', color: 'var(--text-primary)' }}>
                    Executive Profile Summary
                  </h4>
                  <p style={{ margin: 0, fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {parsed.summary}
                  </p>
                </Card>
              )}

              {/* Skills Taxonomy */}
              <Card style={{ padding: '20px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 12px 0', color: 'var(--text-primary)' }}>
                  Skills Taxonomy & Core Competencies
                </h4>
                {(!parsed?.skills || parsed.skills.length === 0) ? (
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    No skills parsed yet. Click 'Re-parse' to run the extraction engine.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {parsed.skills.map((skill, idx) => (
                      <span
                        key={idx}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          backgroundColor: 'rgba(99, 102, 241, 0.12)',
                          border: '1px solid rgba(99, 102, 241, 0.25)',
                          color: 'var(--accent-primary)',
                          fontSize: '12.5px',
                          fontWeight: 500,
                        }}
                      >
                        {skill.name} {skill.years_experience ? `(${skill.years_experience}y)` : ''}
                      </span>
                    ))}
                  </div>
                )}
              </Card>

              {/* Work Experience Chronology */}
              {parsed?.experience && parsed.experience.length > 0 && (
                <Card style={{ padding: '20px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 16px 0', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Briefcase size={16} color="var(--accent-primary)" />
                    Work Experience Chronology
                  </h4>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                    {parsed.experience.map((exp, idx) => (
                      <div
                        key={idx}
                        style={{
                          paddingBottom: idx === parsed.experience!.length - 1 ? 0 : '16px',
                          borderBottom: idx === parsed.experience!.length - 1 ? 'none' : '1px solid var(--border-subtle)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                          <div>
                            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {exp.role}
                            </div>
                            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                              {exp.company}
                            </div>
                          </div>

                          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                            {exp.start_date || 'Past'} — {exp.is_current ? 'Present' : exp.end_date || 'Past'}
                          </div>
                        </div>

                        {exp.description && (
                          <p style={{ margin: '8px 0 10px 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                            {exp.description}
                          </p>
                        )}

                        {exp.skills_used && exp.skills_used.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '6px' }}>
                            {exp.skills_used.map((s, sIdx) => (
                              <span
                                key={sIdx}
                                style={{
                                  padding: '2px 7px',
                                  borderRadius: '4px',
                                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                  fontSize: '11px',
                                  color: 'var(--text-muted)',
                                }}
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Education */}
              {parsed?.education && parsed.education.length > 0 && (
                <Card style={{ padding: '20px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 14px 0', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <GraduationCap size={16} color="var(--accent-secondary)" />
                    Education & Degrees
                  </h4>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {parsed.education.map((edu, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {edu.degree || 'Degree'} {edu.field_of_study ? `in ${edu.field_of_study}` : ''}
                          </div>
                          <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                            {edu.institution}
                          </div>
                        </div>
                        {edu.graduation_year && (
                          <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
                            {edu.graduation_year}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    )}
  </AppLayout>
);
};
