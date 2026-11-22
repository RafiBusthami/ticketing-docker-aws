"""Build the architecture diagram (HTML + PNG).

    pip install diagrams playwright && playwright install chromium
    python docs/diagram/build_diagram.py

Writes docs/architecture.html (editable source) and docs/architecture.png.
Icons are the official AWS Architecture Icons bundled with the `diagrams` package.
"""
import base64
import os
from pathlib import Path

import diagrams

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
RES = Path(os.path.dirname(os.path.dirname(diagrams.__file__))) / "resources"


def icon(rel):
    return "data:image/png;base64," + base64.b64encode((RES / rel).read_bytes()).decode()


ICONS = {
    "client": icon("aws/general/users.png"),
    "github": icon("onprem/vcs/github.png"),
    "igw": icon("aws/network/internet-gateway.png"),
    "ec2": icon("aws/compute/ec2.png"),
    "docker": icon("onprem/container/docker.png"),
    "flask": icon("programming/framework/flask.png"),
    "nginx": icon("onprem/network/nginx.png"),
    "volume": icon("aws/storage/elastic-block-store-ebs-volume.png"),
    "cloud9": icon("aws/devtools/cloud9.png"),
    "ecr": icon("aws/compute/ec2-container-registry.png"),
    "iam": icon("aws/security/identity-and-access-management-iam-aws-sts.png"),
}

BLUE, ORANGE, GREY, GREEN, RED, PURPLE = "#1f6feb", "#c2410c", "#6b7280", "#15803d", "#b91c1c", "#7c3aed"


def node(key, cx, top, title, sub, w=240, size=64, cls=""):
    return f"""
    <div class="node {cls}" style="left:{cx - w // 2}px; top:{top}px; width:{w}px">
      <img src="{ICONS[key]}" style="width:{size}px;height:{size}px">
      <div class="t">{title}</div>
      <div class="s">{sub}</div>
    </div>"""


def box(x, y, w, h, label, cls, icon_key=None):
    img = f'<img src="{ICONS[icon_key]}">' if icon_key else ""
    return (f'<div class="box {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<span>{img}{label}</span></div>')


def arrow(d, color, dash="", label="", lx=0, ly=0, anchor="middle", width=2.4):
    dash_attr = f'stroke-dasharray="{dash}"' if dash else ""
    marker = {BLUE: "mb", ORANGE: "mo", GREY: "mg", GREEN: "mgr", PURPLE: "mp"}[color]
    out = (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" {dash_attr} '
           f'marker-end="url(#{marker})"/>')
    if label:
        tspans = "".join(f'<tspan x="{lx}" dy="{0 if i == 0 else 15}">{t}</tspan>'
                         for i, t in enumerate(label.split("\n")))
        out += f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" class="lbl" fill="{color}">{tspans}</text>'
    return out


def markers():
    return "".join(
        f'<marker id="{m}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
        for m, c in (("mb", BLUE), ("mo", ORANGE), ("mg", GREY), ("mgr", GREEN), ("mp", PURPLE)))


boxes = "".join([
    box(232, 108, 1068, 912, "AWS Cloud &nbsp;&middot;&nbsp; AWS Academy lab account &nbsp;&middot;&nbsp; Region us-east-1", "cloud"),
    box(300, 150, 700, 850, "VPC: LabVPC", "vpc"),
    box(352, 188, 633, 800, "Public Subnet1", "subnet"),
    box(372, 226, 598, 748, "Security group &nbsp;&middot;&nbsp; inbound TCP 8080 from <b>my IP /32 only</b>", "sg"),
    box(392, 266, 563, 694, "EC2 instance &nbsp;&middot;&nbsp; t3.small &nbsp;&middot;&nbsp; Amazon Linux 2023 &nbsp;&middot;&nbsp; Cloud9 env <i>ticketing-dev</i>", "ec2", "ec2"),
    box(412, 316, 523, 404, "Docker Engine &nbsp;&middot;&nbsp; network <i>ticketing-net</i>", "docker", "docker"),
])

nodes = "".join([
    node("client", 110, 372, "Client", "my laptop: curl / browser<br>(public internet)"),
    node("github", 110, 760, "GitHub repository", "code, Dockerfile, scripts"),
    node("igw", 300, 384, "", "", w=60, size=52),
    node("flask", 548, 360, "Service 1: ticket-api", "built this week<br>Flask + gunicorn &middot; :8080<br>non-root, HEALTHCHECK", w=230),
    node("nginx", 806, 360, "Service 2: ticket-web", "planned (Week 13+)<br>nginx &middot; :80 &middot; proxies /api", w=220, cls="planned"),
    node("volume", 548, 570, "Volume <i>ticket-data</i>", "SQLite tickets.db<br>survives restarts", w=230, size=56),
    node("cloud9", 680, 768, "AWS Cloud9 terminal", "git &middot; docker &middot; AWS CLI", w=240, size=56),
    node("ecr", 1185, 330, "Amazon ECR", "private repo<br>ticketing/ticket-api<br>scan on push &middot; AES-256<br>lifecycle: keep 10 images", w=210),
    node("iam", 1185, 640, "IAM temp. credentials", "lab role (voclabs) &#8594;<br>ecr:GetAuthorization-<br>Token &#8594; 12-hour<br>Docker login token", w=210),
])

svg = f"""
<svg class="arrows" width="1800" height="1060" xmlns="http://www.w3.org/2000/svg">
  <defs>{markers()}</defs>
  {arrow("M146,398 L270,398", BLUE, label="1  HTTP :8080", lx=152, ly=390, anchor="start")}
  {arrow("M330,398 L512,398", BLUE, label="2  SG allows my IP", lx=338, ly=390, anchor="start")}
  {arrow("M512,428 L146,428", BLUE, dash="7 5", label="4  JSON response (201/200/204/4xx)", lx=152, ly=446, anchor="start")}
  {arrow("M548,502 L548,566", BLUE, label="3  read / write (SQL)", lx=560, ly=538, anchor="start")}
  {arrow("M740,398 L586,398", GREY, dash="4 4", label="/api proxy (planned)", lx=663, ly=389)}
  {arrow("M146,792 L640,792", GREEN, label="A  git clone", lx=272, ly=784, anchor="start")}
  {arrow("M680,764 L680,724", GREEN, label="B  docker build", lx=692, ly=750, anchor="start")}
  {arrow("M720,796 C900,796 1000,690 1147,672", ORANGE, width=2.6, label="C  aws ecr get-login-password", lx=772, ly=826, anchor="start")}
  {arrow("M935,372 L1148,362", PURPLE, width=2.6, label="D  docker push\n:sha, :latest", lx=1012, ly=332)}
  {arrow("M1148,394 L935,404", PURPLE, dash="7 5", label="E  docker pull\n&#8594; run", lx=1012, ly=428)}
  <text x="1185" y="612" text-anchor="middle" class="lbl" fill="{ORANGE}"><tspan x="1185">token authorises D + E</tspan></text>
  {arrow("M1185,592 L1185,500", ORANGE, dash="3 4", width=1.8)}
</svg>"""

panel = f"""
<div class="panel">
  <h3>Legend</h3>
  <div class="lg"><svg width="46" height="10"><line x1="0" y1="5" x2="46" y2="5" stroke="{BLUE}" stroke-width="3"/></svg>Request / data flow (1&#8211;4)</div>
  <div class="lg"><svg width="46" height="10"><line x1="0" y1="5" x2="46" y2="5" stroke="{GREEN}" stroke-width="3"/></svg>Build flow (A&#8211;B)</div>
  <div class="lg"><svg width="46" height="10"><line x1="0" y1="5" x2="46" y2="5" stroke="{PURPLE}" stroke-width="3"/></svg>Image push / pull to ECR (D&#8211;E)</div>
  <div class="lg"><svg width="46" height="10"><line x1="0" y1="5" x2="46" y2="5" stroke="{ORANGE}" stroke-width="3"/></svg>IAM / authentication (C)</div>
  <div class="lg"><svg width="46" height="10"><rect x="1" y="1" width="44" height="8" fill="none" stroke="{GREY}" stroke-dasharray="4 3"/></svg>Planned (not deployed yet)</div>

  <h3>Security controls</h3>
  <ul>
    <li><b>Network</b> &#8212; instance in a public subnet of LabVPC; security group opens TCP 8080 to <b>my IP /32 only</b>, never 0.0.0.0/0.</li>
    <li><b>IAM</b> &#8212; no access keys stored on disk; Docker logs in to ECR with a short-lived token from the lab role. Least-privilege policy: <code>infra/iam-least-privilege-policy.json</code>.</li>
    <li><b>ECR</b> &#8212; private repository, scan on push, AES-256 encryption, lifecycle rule.</li>
    <li><b>Container</b> &#8212; non-root user, 256 MB / 0.5 CPU limits, health check, restart policy.</li>
    <li><b>App</b> &#8212; input validation, parameterised SQL (no SQL injection).</li>
  </ul>

  <h3>Entity &amp; CRUD endpoints (ticket-api)</h3>
  <table>
    <tr><td class="m post">POST</td><td>/tickets</td><td>Create &#8594; 201</td></tr>
    <tr><td class="m get">GET</td><td>/tickets/{{id}}</td><td>Read &#8594; 200/404</td></tr>
    <tr><td class="m put">PUT</td><td>/tickets/{{id}}</td><td>Update &#8594; 200/404</td></tr>
    <tr><td class="m del">DELETE</td><td>/tickets/{{id}}</td><td>Delete &#8594; 204/404</td></tr>
    <tr class="extra"><td class="m get">GET</td><td>/tickets, /health</td><td>List, health (extra)</td></tr>
  </table>
  <p class="ent"><b>Ticket</b>: ticketId (PK, UUID), title, description, requesterEmail, category, priority, status, createdAt, updatedAt</p>
</div>"""

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Ticketing - Architecture (Track B)</title>
<style>
  body {{ margin:0; background:#fff; font-family:'DM Sans','Fira Sans',Arial,sans-serif; color:#111827; }}
  .canvas {{ position:relative; width:1800px; height:1060px; }}
  h1 {{ position:absolute; left:40px; top:22px; margin:0; font-size:28px; }}
  .subtitle {{ position:absolute; left:40px; top:62px; font-size:15px; color:#4b5563; }}
  .box {{ position:absolute; border-radius:12px; box-sizing:border-box; }}
  .box span {{ position:absolute; left:12px; top:7px; font-size:13px; font-weight:600; color:#374151; display:flex; align-items:center; gap:6px; }}
  .box span img {{ width:22px; height:22px; }}
  .cloud {{ border:2px solid #232f3e; background:#f8fafc; }}
  .cloud span {{ font-size:15px; color:#232f3e; }}
  .vpc {{ border:2px solid #8c4fff; background:#faf7ff; }}
  .vpc span {{ color:#6d28d9; }}
  .subnet {{ border:1.5px solid #16a34a; background:#f0fdf4; }}
  .subnet span {{ color:#15803d; }}
  .sg {{ border:1.8px dashed {RED}; background:#fff; }}
  .sg span {{ color:{RED}; font-weight:600; }}
  .ec2 {{ border:1.5px solid #ea580c; background:#fff7ed; }}
  .ec2 span {{ color:#9a3412; }}
  .docker {{ border:1.5px solid #1d63ed; background:#eff6ff; }}
  .docker span {{ color:#1d4ed8; }}
  .node {{ position:absolute; text-align:center; z-index:2; }}
  .node img {{ display:block; margin:0 auto 5px; }}
  .node .t {{ font-weight:700; font-size:14.5px; }}
  .node .s {{ font-size:12px; color:#374151; line-height:1.35; margin-top:2px; }}
  .node.planned {{ opacity:.62; }}
  .node.planned img {{ outline:2px dashed #9ca3af; outline-offset:4px; border-radius:6px; }}
  .arrows {{ position:absolute; left:0; top:0; z-index:3; pointer-events:none; }}
  .lbl {{ font-size:12.5px; font-weight:600; paint-order:stroke; stroke:#fff; stroke-width:4px; stroke-linejoin:round; white-space:pre; }}
  .panel {{ position:absolute; left:1330px; top:108px; width:440px; height:912px; box-sizing:border-box;
            border:1.5px solid #d1d5db; border-radius:12px; padding:4px 22px; background:#fff; }}
  .panel h3 {{ font-size:16px; margin:16px 0 8px; color:#232f3e; }}
  .lg {{ display:flex; align-items:center; gap:12px; font-size:13.5px; margin:5px 0; }}
  ul {{ margin:0; padding-left:18px; font-size:13px; line-height:1.45; }}
  li {{ margin-bottom:5px; }}
  code {{ font-size:11.5px; background:#f3f4f6; padding:0 3px; border-radius:3px; }}
  table {{ border-collapse:collapse; font-size:13px; width:100%; }}
  td {{ padding:5px 6px; border-bottom:1px solid #e5e7eb; }}
  td.m {{ font-weight:700; font-size:12px; width:58px; }}
  .post {{ color:#15803d; }} .get {{ color:#1f6feb; }} .put {{ color:#b45309; }} .del {{ color:#b91c1c; }}
  tr.extra td {{ color:#6b7280; }}
  .ent {{ font-size:13px; line-height:1.45; margin-top:10px; }}
</style></head>
<body><div class="canvas">
  <h1>Helpdesk Ticketing &#8212; Cloud Solution Architecture</h1>
  <div class="subtitle">Track B: Containers (EC2 + Docker + ECR) &nbsp;&middot;&nbsp; Rafi Busthami (24/532760/TK/58998) &nbsp;&middot;&nbsp; Week 12 &#8212; Design &amp; AWS Setup</div>
  {boxes}
  {nodes}
  {svg}
  {panel}
</div></body></html>"""

(DOCS / "architecture.html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1800, "height": 1060}, device_scale_factor=2)
    page.goto((DOCS / "architecture.html").as_uri())
    page.wait_for_timeout(300)
    page.screenshot(path=str(DOCS / "architecture.png"))
    browser.close()
print("wrote", DOCS / "architecture.png")
