"""User controls render one saved-results layout; processing has no UI side effects."""
import hashlib
import logging
import uuid
from pathlib import Path
import streamlit as st
from services import persist_analysis
from resume_pipeline import analyze_resume
from reports import render_saved_analysis
from certificate_verification import verification_url
from theme import render_hero


def render_user_page(get_connection):
    st.link_button('Verify a certificate',verification_url())
    render_hero()
    values={}
    for field,label in [('name','Name'),('email','Email'),('mobile','Mobile number')]:
        key='candidate_'+field
        backup='_form_'+field
        def remember(widget=key, persistent=backup):
            st.session_state[persistent]=st.session_state[widget]
        values[field]=st.text_input(label,key=key,value=st.session_state.get(backup,''),on_change=remember)
    st.caption('Valid contact details detected in your resume take priority. Form values fill missing details.')
    job_description=st.text_area('Target job description (optional)',key='target_job_description',help='Adds a separate skill-keyword coverage comparison; it does not change the general resume-content rubric.')
    upload=st.file_uploader('Choose your Resume',type=['pdf','docx','png','jpg','jpeg'],key='resume_upload')
    st.caption('Scanned PDFs and PNG/JPG resumes use local text recognition. Check the extracted details; enter missing contact information above.')
    cached=st.session_state.get('_ara_analysis')
    if upload is not None:
        content=upload.getvalue()
        fingerprint=hashlib.sha256(content).hexdigest()
        request_key=hashlib.sha256(content+job_description.encode()+str(sorted(values.items())).encode()).hexdigest()
        if cached and cached.get('key')!=request_key:
            cached=None
            st.session_state.pop('_ara_analysis',None)
        if st.button('Reanalyze Resume' if cached else 'Analyze Resume',key='ara_analyze_btn'):
            try:
                with st.spinner('Extracting resume evidence and evaluating content…'):
                    with get_connection() as conn:
                        result=analyze_resume(conn,content,upload.name,values,job_description=job_description)
                        folder=Path(__file__).resolve().parent/'Uploaded_Resumes'
                        folder.mkdir(exist_ok=True)
                        path=folder/(str(uuid.uuid4())+Path(upload.name).suffix.lower())
                        path.write_bytes(content)
                        result['resume_path']=str(path)
                        saved=persist_analysis(conn,st.session_state['_analysis_owner'],fingerprint,Path(upload.name).name,result,values)
                cached={'key':request_key,'saved_id':saved['analysis_id']}
                st.session_state['_ara_analysis']=cached
                st.session_state['_saved_analysis_id']=saved['analysis_id']
                # Same renderer is used immediately and on every subsequent interaction.
            except ValueError as exc:
                st.error(str(exc))
                return
            except Exception as exc:
                logging.getLogger(__name__).error('Resume analysis failed (%s)',type(exc).__name__)
                st.error('Analysis failed. Your previous saved result is unchanged. Check the server log and retry a readable original resume.')
                return
        if not cached:
            st.info('Click Analyze Resume to process this file. Previous results are hidden until this upload is analyzed.')
            return
        analysis_id=cached['saved_id']
    else:
        analysis_id=st.session_state.get('_saved_analysis_id')
    if analysis_id:
        with get_connection() as conn:
            render_saved_analysis(conn,st.session_state['_analysis_owner'],analysis_id)
    st.caption('The score uses the displayed rubric. It is not an ATS-vendor approval or a universal score shared by other AI tools.')
