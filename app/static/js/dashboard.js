const btn = document.getElementById('newTaskBtn');
const tbody = document.getElementById('taskBody');

btn?.addEventListener('click', () => {
  const row = document.createElement('tr');
  row.innerHTML = `
    <td contenteditable="true">新任务（点击编辑）</td>
    <td contenteditable="true">你</td>
    <td contenteditable="true">2026-05-20</td>
    <td><span class="pill priority-中">中</span></td>
    <td><span class="pill status">待开始</span></td>
  `;
  tbody.prepend(row);
});
