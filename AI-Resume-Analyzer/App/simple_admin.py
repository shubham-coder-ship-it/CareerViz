"""Read-only data/charts, feedback moderation and certificate verification."""
import json
import os
import time
import pandas as pd
import streamlit as st
from services import verify_password, require_admin, audit
from reference_data import reference_index


def render_admin(get_connection):
    st.markdown('<div class="cv-section-label">CAREERVIZ / ADMIN WORKSPACE</div>',unsafe_allow_html=True)
    authenticated=st.session_state.get('_ara_admin_ok') and st.session_state.get('_ara_admin_until',0)>time.time()
    if not authenticated:
        with st.form('simple_admin_login'):
            username=st.text_input('Username')
            password=st.text_input('Password',type='password')
            submit=st.form_submit_button('Login')
        if submit:
            if username==os.getenv('ADMIN_USER','admin') and verify_password(password):
                st.session_state['_ara_admin_ok']=True
                st.session_state['_ara_admin_until']=time.time()+1800
                st.rerun()
            st.error('Incorrect username or password.')
        return
    if st.button('Logout'):
        st.session_state['_ara_admin_ok']=False;st.rerun()
    from admin_analytics import render_analytics
    render_analytics(get_connection)
    with st.expander('Reference dataset and charts'):
        data=reference_index()
        summary=data['summary']
        st.subheader('Reference dataset')
        st.caption('Your supplied data.zip is used automatically for skill-based career matching. No training or model setup is needed.')
        with st.container(horizontal=True):
            st.metric('Resume files',summary.get('files',0))
            st.metric('Usable resumes',summary.get('usable',0))
            st.metric('Career fields',summary.get('categories',0))
        if not data['records']:
            st.info(summary.get('status','Reference data is being prepared.'))
        else:
            frame=pd.DataFrame(data['records'])
            category=st.selectbox('Career field',['All']+sorted(frame.category.unique().tolist()))
            selected=frame if category=='All' else frame[frame.category==category]
            st.dataframe(selected[['file','category','skills','status']],hide_index=True)
            st.caption(f'{len(selected)} matching files. Reference names/contact details and original PDFs are not published in the example library.')
            with st.expander('Charts',expanded=True):
                counts=frame.loc[frame.status=='ready','category'].value_counts()
                from theme import chart_bar_counts, chart_donut
                st.plotly_chart(chart_bar_counts(counts,'Resumes by career field',orientation='h',x_title='Resumes',top_n=30),key='reference_categories')
                st.plotly_chart(chart_donut(frame.status.value_counts(),'Reference file status'),key='reference_status')
                st.caption(f"Unreadable: {summary.get('unreadable',0)} · Duplicates: {summary.get('duplicates',0)}. Unreadable and duplicate files do not contribute to the category profiles.")
    with get_connection() as conn:
        with st.expander('Pin and moderate feedback'):
            rows=conn.execute('SELECT ID,feed_score,comments,Timestamp,pinned,published FROM user_feedback ORDER BY pinned DESC,ID DESC').fetchall()
            if not rows:st.info('No feedback yet.')
            for rid,rating,comment,date,pinned,published in rows:
                with st.container(border=True):
                    st.write(('Pinned · ' if pinned else '')+str(rating)+' / 5 · '+date)
                    st.write(comment)
                    if st.button('Unpin' if pinned else 'Pin',key='pin_'+str(rid)):
                        require_admin();conn.execute('UPDATE user_feedback SET pinned=? WHERE ID=?',(int(not pinned),rid));conn.commit()
                        audit(conn,'feedback_pin',{'id':rid,'pinned':not bool(pinned)});st.rerun()
                    st.caption('Pinning is private. Review the text and remove identifying information before publishing.')
                    reviewed=st.checkbox('I reviewed this feedback for public display',key='moderate_'+str(rid))
                    if st.button('Unpublish' if published else 'Publish feedback text',key='publish_'+str(rid),disabled=not reviewed):
                        require_admin();conn.execute('UPDATE user_feedback SET published=? WHERE ID=?',(int(not published),rid));conn.commit()
                        audit(conn,'feedback_publication',{'id':rid,'published':not bool(published)});st.rerun()
        with st.expander('Verify certificate'):
            code=st.text_input('Certificate code')
            if st.button('Check certificate'):
                from certificate_verification import verify_certificate
                result=verify_certificate(conn,code)
                if result and result['status']=='issued':st.success('Verified certificate');st.write(result)
                else:st.error('Certificate not found or no longer valid.')
