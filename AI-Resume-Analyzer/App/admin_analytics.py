"""Admin-only, read-only analytics of existing saved activity. No traffic tracking."""
import datetime as dt
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from services import require_admin

PALETTE=['#8C78BD','#80ABA1','#C6A477','#9BADD0','#C58EAB','#ADC4A1']
LOCAL_ZONE='Asia/Kolkata'


def local_dates(values):
    normalized=values.astype(str).str.replace('_','T',n=1,regex=False)
    result=pd.to_datetime(normalized,format='mixed',errors='coerce',utc=True).dt.tz_convert(LOCAL_ZONE)
    naive=~normalized.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$',regex=True,case=False)
    if naive.any():
        result.loc[naive]=pd.to_datetime(normalized.loc[naive],format='mixed',errors='coerce').dt.tz_localize(LOCAL_ZONE)
    return result


def load_activity(conn):
    entries=[]
    for row in conn.execute('SELECT id,owner,filename,created_at,result FROM analyses ORDER BY created_at DESC'):
        try:
            result=json.loads(row[4])
            entries.append({'Analysis':row[0],'Session':row[1],'File':row[2],'Timestamp':row[3],
                            'Name':result.get('candidate',{}).get('name','Unavailable'),
                            'Score':result.get('score'), 'Career field':result.get('predicted_field','Unavailable'),
                            'Experience':result.get('experience_level','Unavailable'),
                            'Rubric':result.get('scoring_version','legacy'),
                            'Format':row[2].rsplit('.',1)[-1].upper() if '.' in row[2] else 'Unknown'})
        except (ValueError,TypeError):
            continue
    columns=['Analysis','Session','File','Timestamp','Name','Score','Career field','Experience','Rubric','Format']
    frame=pd.DataFrame(entries,columns=columns)
    frame['Date']=local_dates(frame.Timestamp)
    frame['Score']=pd.to_numeric(frame.Score,errors='coerce')
    feedback=pd.read_sql_query('SELECT ID,feed_score,Timestamp,published,pinned FROM user_feedback',conn)
    feedback['Date']=local_dates(feedback.Timestamp)
    feedback['Rating']=pd.to_numeric(feedback.feed_score,errors='coerce')
    certs=pd.read_sql_query('SELECT code,analysis_id,issued_at,status FROM certificates',conn)
    certs['Date']=local_dates(certs.issued_at)
    return frame,feedback,certs


def date_slice(frame,start,end):
    if start>end:raise ValueError('Start date must be on or before end date.')
    return frame.loc[frame.Date.notna() & (frame.Date.dt.date>=start) & (frame.Date.dt.date<=end)].copy()


def filter_activity(frame,start,end,fields=None,rubric='All versions',score_range=(0,100)):
    result=date_slice(frame,start,end)
    if fields:result=result[result['Career field'].isin(fields)]
    if rubric!='All versions':result=result[result.Rubric==rubric]
    return result[result.Score.between(*score_range)]


def csv_download(frame):
    safe=frame.drop(columns=['Session'],errors='ignore').copy()
    for column in safe.select_dtypes(include=['object','str']).columns:
        safe[column]=safe[column].map(lambda v: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v)
    return safe.to_csv(index=False).encode('utf-8-sig')


def style_chart(figure,height=325):
    figure.update_layout(height=height,margin=dict(l=12,r=12,t=35,b=16),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                         font=dict(family='Inter, sans-serif',color='#7F7B92'),legend_title_text='',title_font_size=15)
    figure.update_xaxes(gridcolor='rgba(151,139,174,.13)',zeroline=False)
    figure.update_yaxes(gridcolor='rgba(151,139,174,.13)',zeroline=False)
    return figure


def render_analytics(get_connection):
    require_admin()
    with get_connection() as conn:
        all_activity,all_feedback,all_certs=load_activity(conn)
    st.markdown('<div class="cv-section-label">PERFORMANCE OVERVIEW</div>',unsafe_allow_html=True)
    st.header('A clearer view of your activity')
    st.caption('Saved resume analyses, submission sessions and feedback. Dates use India time (Asia/Kolkata). Page views and all website visitors are not tracked by the current database.')
    today=pd.Timestamp.now(tz=LOCAL_ZONE).date()
    valid_dates=pd.concat([all_activity.Date,all_feedback.Date,all_certs.Date]).dropna()
    first=min(valid_dates.dt.date.min(),today) if not valid_dates.empty else today
    with st.container(border=True):
        period=st.segmented_control('Time period',['Last 7 days','Last 30 days','Last 90 days','All time','Custom'],default='All time',key='analytics_period')
        if period=='Custom':
            left,right=st.columns(2)
            start=left.date_input('Start date',first,key='analytics_start')
            end=right.date_input('End date',today,key='analytics_end')
        else:
            days={'Last 7 days':7,'Last 30 days':30,'Last 90 days':90}
            start=today-dt.timedelta(days=days[period]-1) if period in days else first
            end=today
        if start>end:
            st.error('Choose an end date on or after the start date.');return
        with st.container(horizontal=True):
            fields=st.multiselect('Career fields',sorted(all_activity['Career field'].dropna().unique()),key='analytics_fields')
            versions=['All versions']+sorted(all_activity.Rubric.dropna().unique())
            rubric=st.selectbox('Scoring version',versions,index=0,key='analytics_rubric')
            scores=st.slider('Resume score',0,100,(0,100),key='analytics_score')
    activity=filter_activity(all_activity,start,end,fields,rubric,scores)
    feedback=date_slice(all_feedback,start,end)
    certs=date_slice(all_certs,start,end)
    linked_certs=certs[certs.analysis_id.isin(activity.Analysis)]
    average=activity.Score.mean() if activity.Rubric.nunique()<=1 else float('nan')
    with st.container(horizontal=True):
        st.metric('Resume analyses',len(activity),border=True)
        st.metric('Analysis sessions',activity.Session.nunique(),help='Distinct saved submission-session tokens, not distinct people or all website visitors.',border=True)
        st.metric('Average resume score',f'{average:.1f} / 100' if pd.notna(average) else '—',help='Select one scoring version to compare scores. Different rubric versions are not averaged together.',border=True)
        st.metric('Certificates issued',int((linked_certs.status=='issued').sum()),help='Issued within the date range and linked to the filtered analyses.',border=True)
    st.caption(f"{start:%d %b %Y} – {end:%d %b %Y} · {len(activity)} matching analyses · Feedback uses the date range only.")
    undated=int(all_activity.Date.isna().sum()+all_feedback.Date.isna().sum()+all_certs.Date.isna().sum())
    if undated:st.caption(f'{undated} records have missing or unreadable dates and are excluded from date-based analytics.')
    if rubric=='All versions' and activity.Rubric.nunique()>1:
        st.info('This selection includes different scoring rubrics. Use the scoring-version filter for meaningful score comparisons.')
    if activity.empty:
        st.info('No saved analyses match these filters. Try All time or broaden the score and career filters.')
    else:
        left,right=st.columns([1.5,1])
        with left,st.container(border=True):
            st.subheader('Analysis activity')
            trend=activity.groupby(activity.Date.dt.date).size().rename('Analyses').reset_index(name='Analyses')
            calendar=pd.DataFrame({'Date':pd.date_range(start,end,freq='D').date})
            trend=calendar.merge(trend,on='Date',how='left').fillna({'Analyses':0})
            fig=px.area(trend,x='Date',y='Analyses',color_discrete_sequence=PALETTE)
            fig.update_traces(line=dict(width=2.5),fillcolor='rgba(140,120,189,.14)')
            st.plotly_chart(style_chart(fig),key='analytics_activity')
        with right,st.container(border=True):
            st.subheader('Career interests')
            counts=activity['Career field'].value_counts().head(8).rename_axis('Career field').reset_index(name='Analyses')
            fig=px.pie(counts,names='Career field',values='Analyses',hole=.72,color_discrete_sequence=PALETTE)
            fig.update_traces(textinfo='none')
            fig.update_layout(legend=dict(orientation='h',y=-.1))
            st.plotly_chart(style_chart(fig),key='analytics_careers')
        left,right=st.columns(2)
        with left,st.container(border=True):
            st.subheader('Resume score distribution')
            fig=px.histogram(activity,x='Score',color='Rubric' if activity.Rubric.nunique()>1 else None,nbins=10,color_discrete_sequence=PALETTE)
            fig.update_layout(bargap=.15,xaxis_range=[0,100],yaxis_title='Analyses')
            st.plotly_chart(style_chart(fig),key='analytics_scores')
        with right,st.container(border=True):
            st.subheader('Experience mix')
            counts=activity.Experience.value_counts().rename_axis('Experience').reset_index(name='Analyses')
            fig=px.bar(counts,x='Analyses',y='Experience',orientation='h',color='Experience',color_discrete_sequence=PALETTE)
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_chart(fig),key='analytics_experience')
        with st.expander('File formats and scoring versions'):
            st.dataframe(activity.groupby(['Format','Rubric']).size().reset_index(name='Analyses'),hide_index=True)
    with st.container(border=True):
        st.subheader('Feedback pulse')
        with st.container(horizontal=True):
            st.metric('Feedback received',len(feedback))
            rating=feedback.Rating.mean()
            st.metric('Average rating',f'{rating:.1f} / 5' if pd.notna(rating) else '—')
            st.metric('Published comments',int(feedback.published.sum()))
            st.metric('Pinned comments',int(feedback.pinned.sum()))
    with st.container(border=True):
        st.subheader('Activity records')
        display=activity.drop(columns=['Session','Timestamp'],errors='ignore')
        st.dataframe(display,hide_index=True)
        st.download_button('Export filtered records',csv_download(display),file_name=f'CareerViz_activity_{start}_{end}.csv',mime='text/csv',disabled=activity.empty)
