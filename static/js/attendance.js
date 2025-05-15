document.addEventListener('DOMContentLoaded', function() {
    const shareBtn = document.getElementById('share-btn');
    const shareLinkInput = document.getElementById('share-link');
    const shareLinkContainer = document.getElementById('share-link-container');
    const copyBtn = document.getElementById('copy-btn');
    const filterBtn = document.getElementById('filter-btn');
    const addRecordBtn = document.getElementById('add-record-btn');

    // Xác thực định dạng thời gian HH:MM:SS
    function validateTime(time) {
        return /^([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$/.test(time);
    }

    // Xử lý chia sẻ link
    if (shareBtn) {
        shareBtn.addEventListener('click', function() {
            const period = document.querySelector('select[name="period"]').value;
            fetch('/share_attendance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `period=${period}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    shareLinkInput.value = data.share_url;
                    shareLinkContainer.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Lỗi khi tạo link chia sẻ!');
            });
        });
    }

    // Xử lý sao chép link
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            shareLinkInput.select();
            document.execCommand('copy');
            alert('Đã sao chép link!');
        });
    }

    // Xử lý nhấp vào ô trạng thái trong bảng thống kê
    document.querySelectorAll('td[data-user-id]').forEach(cell => {
        cell.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            const date = this.getAttribute('data-date');
            fetch('/admin_attendance_details', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `user_id=${userId}&date=${date}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }
                // Cập nhật modal chi tiết
                document.getElementById('employee-name').textContent = cell.parentElement.querySelector('td').nextElementSibling.textContent;
                document.getElementById('date').textContent = new Date(date).toLocaleDateString('vi-VN');
                document.getElementById('checkin-morning').textContent = data['Vào Sáng'].time;
                document.getElementById('checkout-morning').textContent = data['Ra Sáng'].time;
                document.getElementById('checkin-afternoon').textContent = data['Vào Chiều'].time;
                document.getElementById('checkout-afternoon').textContent = data['Ra Chiều'].time;
                document.getElementById('hours-worked').textContent = data.hours_worked + ' giờ';
                // Hiển thị ghi chú
                document.getElementById('checkin-morning-note').textContent = data['Vào Sáng'].note ? `(Ghi chú: ${data['Vào Sáng'].note})` : '';
                document.getElementById('checkout-morning-note').textContent = data['Ra Sáng'].note ? `(Ghi chú: ${data['Ra Sáng'].note})` : '';
                document.getElementById('checkin-afternoon-note').textContent = data['Vào Chiều'].note ? `(Ghi chú: ${data['Vào Chiều'].note})` : '';
                document.getElementById('checkout-afternoon-note').textContent = data['Ra Chiều'].note ? `(Ghi chú: ${data['Ra Chiều'].note})` : '';
                document.getElementById('user-id').value = userId;
                document.getElementById('attendance-date').value = date;

                const photosContainer = document.getElementById('photos');
                photosContainer.innerHTML = '';
                if (data.photos && data.photos.length > 0) {
                    data.photos.forEach(photo => {
                        const img = document.createElement('img');
                        img.src = photo;
                        img.style.maxWidth = '100px';
                        img.style.marginRight = '10px';
                        img.style.cursor = 'pointer';
                        img.classList.add('img-thumbnail');
                        img.addEventListener('click', () => {
                            document.getElementById('modal-photo').src = photo;
                            $('#photoModal').modal('show');
                        });
                        photosContainer.appendChild(img);
                    });
                } else {
                    photosContainer.textContent = 'Không có ảnh';
                }

                $('#attendanceDetailsModal').modal('show');
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Lỗi khi lấy chi tiết chấm công!');
            });
        });
    });

    // Xử lý tab Chi tiết chấm công
    function loadAttendanceRecords() {
        const userId = document.getElementById('details-user-id').value;
        const period = document.getElementById('details-period').value;
        const tbody = document.querySelector('#details-table tbody');
        tbody.innerHTML = '<tr><td colspan="10" class="text-center"><div class="spinner-border text-primary" role="status"><span class="sr-only">Loading...</span></div></td></tr>';
        fetch('/admin_attendance_records', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `user_id=${userId}&period=${period}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                tbody.innerHTML = '<tr><td colspan="10" class="text-center">Không có dữ liệu</td></tr>';
                return;
            }

            // Nhóm bản ghi theo user_id và date
            const groupedRecords = {};
            data.records.forEach(record => {
                const key = `${record.user_id}_${record.date}`;
                if (!groupedRecords[key]) {
                    groupedRecords[key] = {
                        user_id: record.user_id,
                        full_name: record.full_name,
                        date: record.date,
                        records: {},
                        hours_worked: record.hours_worked
                    };
                }
                groupedRecords[key].records[record.type] = {
                    time: record.time,
                    photo: record.photo,
                    record_id: record.id,
                    note: record.note // Lưu ghi chú
                };
            });

            tbody.innerHTML = '';
            Object.values(groupedRecords).forEach(group => {
                const tr = document.createElement('tr');
                const types = ['Vào Sáng', 'Ra Sáng', 'Vào Chiều', 'Ra Chiều'];
                const timeCells = types.map(type => {
                    const record = group.records[type] || {};
                    return `<td class="${record.time ? 'time-present' : 'time-missing'}">${record.time || 'Chưa chấm'}</td>`;
                }).join('');
                const photoCells = types.map(type => {
                    const record = group.records[type] || {};
                    return record.photo
                        ? `<img src="${record.photo}" class="record-photo" data-photo="${record.photo}" title="${type}">`
                        : `<div class="record-photo missing" title="${type}"></div>`;
                }).join('');
                // Lấy ghi chú (ưu tiên ghi chú đầu tiên có giá trị, hoặc để trống)
                const note = types
                    .map(type => group.records[type]?.note)
                    .find(note => note) || '';
                tr.innerHTML = `
                    <td>${group.full_name}</td>
                    <td>${new Date(group.date).toLocaleDateString('vi-VN')}</td>
                    ${timeCells}
                    <td>${group.hours_worked} giờ</td>
                    <td class="photo-container">${photoCells}</td>
                    <td>${note}</td>
                    <td>
                        <div class="btn-group">
                            <button type="button" class="btn btn-sm btn-primary dropdown-toggle" data-toggle="dropdown">
                                <i class="fas fa-edit"></i> Chỉnh sửa
                            </button>
                            <div class="dropdown-menu">
                                ${types.map(type => `
                                    <a class="dropdown-item edit-record-btn" href="#" 
                                       data-type="${type}" 
                                       data-record-id="${group.records[type]?.record_id || ''}" 
                                       data-timestamp="${group.records[type]?.time || ''}" 
                                       data-note="${group.records[type]?.note || ''}">
                                        <i class="fas fa-${type.includes('Vào') ? 'sign-in-alt' : 'sign-out-alt'}"></i> ${type}
                                    </a>
                                `).join('')}
                                <a class="dropdown-item delete-record-btn" href="#" 
                                   data-user-id="${group.user_id}" 
                                   data-date="${group.date}">
                                    <i class="fas fa-trash"></i> Xóa ngày
                                </a>
                            </div>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Xử lý nhấp vào ảnh
            document.querySelectorAll('.record-photo').forEach(img => {
                img.addEventListener('click', () => {
                    const photo = img.getAttribute('data-photo');
                    if (photo) {
                        document.getElementById('modal-photo').src = photo;
                        $('#photoModal').modal('show');
                    }
                });
            });

            // Xử lý nút Chỉnh sửa
            document.querySelectorAll('.edit-record-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const recordId = this.getAttribute('data-record-id');
                    const timestamp = this.getAttribute('data-timestamp');
                    const type = this.getAttribute('data-type');
                    const note = this.getAttribute('data-note');
                    document.getElementById('edit-record-id').value = recordId;
                    document.getElementById('edit-timestamp').value = timestamp;
                    document.getElementById('edit-type').value = type;
                    document.getElementById('edit-note').value = note || '';
                    $('#editAttendanceModal').modal('show');
                });
            });

            // Xử lý nút Xóa ngày
            document.querySelectorAll('.delete-record-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const userId = this.getAttribute('data-user-id');
                    const date = this.getAttribute('data-date');
                    if (confirm('Bạn có chắc muốn xóa tất cả bản ghi chấm công của ngày này?')) {
                        fetch('/admin_delete_attendance', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/x-www-form-urlencoded',
                            },
                            body: `user_id=${userId}&date=${date}`
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert(data.success);
                                loadAttendanceRecords();
                            } else {
                                alert(data.error);
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            alert('Lỗi khi xóa bản ghi!');
                        });
                    }
                });
            });
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Lỗi khi tải danh sách chấm công!');
            tbody.innerHTML = '<tr><td colspan="10" class="text-center">Lỗi tải dữ liệu</td></tr>';
        });
    }

    // Tải dữ liệu khi tab Chi tiết được kích hoạt
    $('#details-tab').on('shown.bs.tab', function() {
        loadAttendanceRecords();
    });

    // Xử lý nút Lọc
    if (filterBtn) {
        filterBtn.addEventListener('click', loadAttendanceRecords);
    }

    // Xử lý nút Thêm chấm công
    if (addRecordBtn) {
        addRecordBtn.addEventListener('click', function() {
            document.getElementById('add-date').value = new Date().toISOString().split('T')[0];
            document.getElementById('add-timestamp').value = '';
            document.getElementById('add-type').value = 'Vào Sáng';
            document.getElementById('add-photo').value = '';
            document.getElementById('add-note').value = '';
            $('#addAttendanceModal').modal('show');
        });
    }

    // Xử lý form chỉnh sửa chấm công
    document.getElementById('edit-attendance-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const timestamp = document.getElementById('edit-timestamp').value;
        if (!validateTime(timestamp)) {
            alert('Thời gian phải có định dạng HH:MM:SS!');
            return;
        }
        const formData = new FormData();
        formData.append('record_id', document.getElementById('edit-record-id').value);
        formData.append('timestamp', timestamp);
        formData.append('type', document.getElementById('edit-type').value);
        formData.append('note', document.getElementById('edit-note').value);
        const photoFile = document.getElementById('edit-photo').files[0];
        if (photoFile) {
            if (photoFile.size > 5 * 1024 * 1024) {
                alert('Ảnh quá lớn, tối đa 5MB!');
                return;
            }
            const reader = new FileReader();
            reader.onload = function(event) {
                formData.append('photo_data', event.target.result);
                submitEditForm(formData);
            };
            reader.readAsDataURL(photoFile);
        } else {
            formData.append('photo_data', '');
            submitEditForm(formData);
        }
    });

    function submitEditForm(formData) {
        fetch('/admin_edit_attendance', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert(data.success);
                $('#editAttendanceModal').modal('hide');
                loadAttendanceRecords();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Lỗi khi cập nhật chấm công!');
        });
    }

    // Xử lý form thêm chấm công
    document.getElementById('add-attendance-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const timestamp = document.getElementById('add-timestamp').value;
        if (!validateTime(timestamp)) {
            alert('Thời gian phải có định dạng HH:MM:SS!');
            return;
        }
        const formData = new FormData();
        formData.append('user_id', document.getElementById('add-user-id').value);
        formData.append('date', document.getElementById('add-date').value);
        formData.append('timestamp', timestamp);
        formData.append('type', document.getElementById('add-type').value);
        formData.append('note', document.getElementById('add-note').value);
        const photoFile = document.getElementById('add-photo').files[0];
        if (photoFile) {
            if (photoFile.size > 5 * 1024 * 1024) {
                alert('Ảnh quá lớn, tối đa 5MB!');
                return;
            }
            const reader = new FileReader();
            reader.onload = function(event) {
                formData.append('photo_data', event.target.result);
                submitAddForm(formData);
            };
            reader.readAsDataURL(photoFile);
        } else {
            formData.append('photo_data', '');
            submitAddForm(formData);
        }
    });

    function submitAddForm(formData) {
        fetch('/admin_add_attendance', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert(data.success);
                $('#addAttendanceModal').modal('hide');
                loadAttendanceRecords();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Lỗi khi thêm chấm công!');
        });
    }
});