"""Compatibility API using the application's one shared extraction pipeline."""
from pathlib import Path


class ResumeParser:
    def __init__(self, resume, skills_file=None, custom_regex=None):
        from resume_pipeline import parse_resume
        if hasattr(resume,'getvalue'):
            content=resume.getvalue()
            filename=getattr(resume,'name','resume.pdf')
        else:
            path=Path(resume)
            content=path.read_bytes()
            filename=path.name
        _, self._details, _ = parse_resume(content,filename)

    def get_extracted_data(self):
        return dict(self._details)


def resume_result_wrapper(resume):
    return ResumeParser(resume).get_extracted_data()
