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
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)
    english_name: Mapped[str] = mapped_column(String(200), default='')
    region: Mapped[str] = mapped_column(String(200), default='')
    qs: Mapped[float] = mapped_column(Float, default=0.0)
    usnews: Mapped[float] = mapped_column(Float, default=0.0)
    the: Mapped[float] = mapped_column(Float, default=0.0)
    arwu: Mapped[float] = mapped_column(Float, default=0.0)
    history_data: Mapped[str] = mapped_column(Text, default='')

@app.before_request
def init_db_once():
    db.create_all()

@app.get('/')
def index():
    school_name = request.args.get('school_name', '').strip()
    english_name = request.args.get('english_name', '').strip()
    region = request.args.get('region', '').strip()

    query = Ranking.query
    if school_name:
        query = query.filter(Ranking.school_name.ilike(f'%{school_name}%'))
    if english_name:
        query = query.filter(Ranking.english_name.ilike(f'%{english_name}%'))
    if region:
        query = query.filter(Ranking.region.ilike(f'%{region}%'))

    rankings = query.order_by(Ranking.rank.asc()).all()
    return render_template('index.html', rankings=rankings, school_name=school_name, english_name=english_name, region=region)

@app.get('/admin')
def admin():
    rankings = Ranking.query.order_by(Ranking.rank.asc()).all()
    total = len(rankings)
    avg_score = round(sum(r.qs for r in rankings) / total, 1) if total else 0
    total_locations = len({r.region for r in rankings if r.region})
    return render_template('admin.html', rankings=rankings, total=total, avg_score=avg_score, total_locations=total_locations)

@app.post('/admin/add')
def add_ranking():
    row = Ranking(
        rank=int(request.form.get('rank', 0)),
        school_name=request.form.get('school_name', '').strip(),
        english_name=request.form.get('english_name', '').strip(),
        region=request.form.get('region', '').strip(),
        qs=float(request.form.get('qs', 0) or 0),
        usnews=float(request.form.get('usnews', 0) or 0),
        the=float(request.form.get('the', 0) or 0),
        arwu=float(request.form.get('arwu', 0) or 0),
        history_data=request.form.get('history_data', '').strip(),
    )
    if not row.school_name or row.rank <= 0:
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
    row.school_name = request.form.get('school_name', row.school_name).strip()
    row.english_name = request.form.get('english_name', row.english_name).strip()
    row.region = request.form.get('region', row.region).strip()
    row.qs = float(request.form.get('qs', row.qs) or 0)
    row.usnews = float(request.form.get('usnews', row.usnews) or 0)
    row.the = float(request.form.get('the', row.the) or 0)
    row.arwu = float(request.form.get('arwu', row.arwu) or 0)
    row.history_data = request.form.get('history_data', row.history_data).strip()

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
                school_name=(r.get('school_name') or '').strip(),
                english_name=(r.get('english_name') or '').strip(),
                region=(r.get('region') or '').strip(),
                qs=float(r.get('qs', 0) or 0),
                usnews=float(r.get('usnews', 0) or 0),
                the=float(r.get('the', 0) or 0),
                arwu=float(r.get('arwu', 0) or 0),
                history_data=(r.get('history_data') or '').strip(),
            )
            if row.rank > 0 and row.school_name:
                db.session.add(row)
                count += 1
        except Exception:
            continue
    db.session.commit()
    flash(f'CSV 导入完成，共 {count} 条记录', 'success')
    return redirect(url_for('admin'))

@app.get('/admin/template.csv')
def download_template():
    sample = 'rank,school_name,english_name,region,qs,usnews,the,arwu,history_data\n1,示例大学,Sample University,美国,98.2,92.5,88.0,85.5,2023:95|2024:97|2025:98\n'
    return send_file(
        io.BytesIO(sample.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='ranking_template.csv'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
