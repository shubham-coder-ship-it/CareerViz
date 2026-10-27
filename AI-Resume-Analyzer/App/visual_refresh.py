"""Presentation only: reference-video inspired panels and soft colour system."""
from pathlib import Path
import streamlit as st


def inject_refresh():
    style=Path(__file__).with_name('assets').joinpath('career_refresh.css').read_text(encoding='utf-8')
    st.markdown('<style>'+style+'</style>',unsafe_allow_html=True)


def render_hero(total_users=None):
    st.markdown('''
    <section class="ara-hero cv-hero">
      <div class="ara-hero-grid">
        <div class="ara-hero-copy">
          <span class="cv-eyebrow"><span class="cv-status-dot"></span> A LITTLE CLARITY. A BIG NEXT STEP.</span>
          <h1>Your experience.<br>A <span class="accent">clearer direction.</span></h1>
          <p>Discover the strengths in your resume, see where you can grow, and explore career paths that fit your skills.</p>
          <div class="cv-hero-tags"><span>Thoughtful feedback</span><span>Transparent scoring</span><span>Career discovery</span></div>
          <div class="cv-hero-foot"><span class="cv-line"></span> Your next chapter starts with what you already know.</div>
        </div>
        <div class="ara-hero-media cv-art" aria-hidden="true">
          <div class="cv-orbit cv-orbit-one"></div><div class="cv-orbit cv-orbit-two"></div>
          <div class="cv-resume-card">
            <div class="cv-card-top"><span class="cv-card-icon">CV</span><span>YOUR NEXT CHAPTER<br><b>A little more you.</b></span><i></i></div>
            <div class="cv-paper-line long"></div><div class="cv-paper-line medium"></div>
            <div class="cv-card-section">EXPERIENCE & POTENTIAL</div>
            <div class="cv-paper-line long"></div><div class="cv-paper-line short"></div>
            <div class="cv-chip-row"><span>Your skills</span><span>Your story</span></div>
            <div class="cv-paper-line medium"></div><div class="cv-paper-line long"></div>
            <div class="cv-card-bottom"><span class="cv-spark">✧</span><span>Make your strengths visible</span></div>
          </div>
          <div class="cv-floating-label"><span class="cv-status-dot"></span> A fresh perspective</div>
        </div>
      </div>
    </section>''',unsafe_allow_html=True)
