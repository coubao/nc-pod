from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rankings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Ranking(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    school: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), default='')
    score: Mapped[float] = mapped_column(Float, default=0.0)
    tuition: Mapped[str] = mapped_column(String(120), default='')
    notes: Mapped[str] = mapped_column(Text, default='')

@app.before_request
def init_db_once():
    db.create_all()

@app.get('/')
def index():
    q = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()

    query = Ranking.query
    if q:
        query = query.filter(Ranking.school.ilike(f'%{q}%'))
    if location:
        query = query.filter(Ranking.location.ilike(f'%{location}%'))

    rankings = query.order_by(Ranking.rank.asc()).all()
    locations = [x[0] for x in db.session.query(Ranking.location).distinct().filter(Ranking.location != '').all()]
    return render_template('index.html', rankings=rankings, q=q, location=location, locations=sorted(locations))

@app.get('/admin')
def admin():
    rankings = Ranking.query.order_by(Ranking.rank.asc()).all()
    total = len(rankings)
    avg_score = round(sum(r.score for r in rankings) / total, 1) if total else 0
    total_locations = len({r.location for r in rankings if r.location})
    return render_template('admin.html', rankings=rankings, total=total, avg_score=avg_score, total_locations=total_locations)

@app.post('/admin/add')
def add_ranking():
    row = Ranking(
        rank=int(request.form.get('rank', 0)),
        school=request.form.get('school', '').strip(),
        location=request.form.get('location', '').strip(),
        score=float(request.form.get('score', 0) or 0),
        tuition=request.form.get('tuition', '').strip(),
        notes=request.form.get('notes', '').strip(),
    )
    if not row.school or row.rank <= 0:
        flash('Rank 和 School 为必填项', 'danger')
        return redirect(url_for('admin'))

    db.session.add(row)
    db.session.commit()
    flash('新增成功', 'success')
    return redirect(url_for('admin'))

@app.post('/admin/update/<int:row_id>')
def update_ranking(row_id: int):
    row = Ranking.query.get_or_404(row_id)
    row.rank = int(request.form.get('rank', row.rank))
    row.school = request.form.get('school', row.school).strip()
    row.location = request.form.get('location', row.location).strip()
    row.score = float(request.form.get('score', row.score) or 0)
    row.tuition = request.form.get('tuition', row.tuition).strip()
    row.notes = request.form.get('notes', row.notes).strip()

    db.session.commit()
    flash('更新成功', 'success')
    return redirect(url_for('admin'))

@app.post('/admin/delete/<int:row_id>')
def delete_ranking(row_id: int):
    row = Ranking.query.get_or_404(row_id)
    db.session.delete(row)
    db.session.commit()
    flash('删除成功', 'success')
    return redirect(url_for('admin'))

@app.post('/admin/upload-csv')
def upload_csv():
    f = request.files.get('csv_file')
    if not f:
        flash('请上传CSV文件', 'danger')
        return redirect(url_for('admin'))

    data = io.StringIO(f.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(data)

    Ranking.query.delete()
    count = 0
    for r in reader:
        try:
            row = Ranking(
                rank=int(r.get('rank', 0)),
                school=(r.get('school') or '').strip(),
                location=(r.get('location') or '').strip(),
                score=float(r.get('score', 0) or 0),
                tuition=(r.get('tuition') or '').strip(),
                notes=(r.get('notes') or '').strip(),
            )
            if row.rank > 0 and row.school:
                db.session.add(row)
                count += 1
        except Exception:
            continue
    db.session.commit()
    flash(f'CSV 导入完成，共 {count} 条记录', 'success')
    return redirect(url_for('admin'))

@app.get('/admin/template.csv')
def download_template():
    sample = 'rank,school,location,score,tuition,notes\n1,Sample University,CA,98.2,$56000,Strong STEM program\n'
    return send_file(
        io.BytesIO(sample.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='ranking_template.csv'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
