# Attribution and licensing

CareerViz development and customization: Copyright (c) 2026 Shubham Sharma.

CareerViz is distributed under the GNU General Public License, version 3. See
[LICENSE](LICENSE) for the complete terms.

The project includes modified compatibility code derived from
[pyresparser by Omkar Pathak](https://github.com/OmkarPathak/pyresparser), including
the utilities, constants and skill vocabulary under
`AI-Resume-Analyzer/App/pyresparser/`. The upstream project is licensed under
[GPL-3.0](https://github.com/OmkarPathak/pyresparser/blob/master/LICENSE).
Existing author comments have been retained. Compatibility parsing now delegates
to CareerViz's shared pipeline, and the utilities were adapted to remove the main
application's dependency on spaCy and runtime NLP downloads.

Other third-party libraries retain their respective copyrights and licences.
The project licence does not grant rights to private reference datasets or real
users' resumes, which are not included in this repository. The resume shown in
the README is an original fictional example, not a real applicant's document.
