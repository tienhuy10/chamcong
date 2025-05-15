$(document).ready(function() {
    // Xử lý thêm nhân viên
    $('#add-employee-btn').on('click', function() {
        $('#employeeModalLabel').text('Thêm nhân viên');
        $('#employeeForm')[0].reset();
        $('#user_id').val('');
        $('#password-required').show();
        $('#password').prop('required', true);
        $('.select2').val('employee').trigger('change'); // Mặc định vai trò là nhân viên
        $('#is_active').val('1').trigger('change'); // Mặc định kích hoạt
        $('#employeeModal').modal('show');
    });

    // Xử lý form thêm/sửa nhân viên
    $('#employeeForm').on('submit', function(e) {
        e.preventDefault();
        console.log('Employee form submitted');
        
        var userId = $('#user_id').val();
        var url = userId ? '/admin_edit_employee' : '/admin_add_employee';
        
        $.ajax({
            url: url,
            type: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                console.log('Employee AJAX success:', response);
                if (response.success) {
                    toastr.success(response.success);
                    $('#employeeModal').modal('hide');
                    location.reload(); // Tải lại trang để cập nhật bảng
                } else {
                    toastr.error(response.error || 'Lỗi khi lưu nhân viên!');
                }
            },
            error: function(xhr) {
                console.log('Employee AJAX error:', xhr.responseText);
                toastr.error('Lỗi khi lưu nhân viên!');
            }
        });
    });

    // Xử lý sửa nhân viên
    $(document).on('click', '.edit-employee-btn', function() {
        var userId = $(this).data('user-id');
        console.log('Edit employee button clicked, userId:', userId);
        
        var row = $(`tr[data-user-id="${userId}"]`);
        $('#employeeModalLabel').text('Sửa nhân viên');
        $('#user_id').val(userId);
        $('#username').val(row.find('td:nth-child(3)').text());
        $('#full_name').val(row.find('td:nth-child(2)').text());
        $('#department').val(row.find('td:nth-child(4)').text() === 'Chưa xác định' ? '' : row.find('td:nth-child(4)').text());
        $('#position').val(row.find('td:nth-child(5)').text() === 'Chưa xác định' ? '' : row.find('td:nth-child(5)').text());
        $('#email').val(row.find('td:nth-child(6)').text() === 'Chưa xác định' ? '' : row.find('td:nth-child(6)').text());
        $('#phone').val(row.find('td:nth-child(7)').text() === 'Chưa xác định' ? '' : row.find('td:nth-child(7)').text());
        $('#password-required').hide();
        $('#password').prop('required', false);
        // Lấy trạng thái từ checkbox
        var isActive = row.find('.toggle-active').prop('checked') ? '1' : '0';
        $('#is_active').val(isActive).trigger('change');
        // Vai trò cần lấy từ server hoặc ẩn trong data attribute
        $('#role').val('employee').trigger('change'); // Giả định, cần lấy từ server nếu có
        $('#employeeModal').modal('show');
    });

    // Xử lý toggle trạng thái
    $(document).on('change', '.toggle-active', function() {
        var userId = $(this).data('user-id');
        var isChecked = $(this).prop('checked');
        console.log('Toggle active changed, userId:', userId, 'isChecked:', isChecked);
        
        if (confirm('Bạn có chắc chắn muốn thay đổi trạng thái nhân viên này?')) {
            $.ajax({
                url: '/admin_toggle_active',
                type: 'POST',
                data: { user_id: userId },
                success: function(response) {
                    console.log('Toggle AJAX success:', response);
                    if (response.success) {
                        toastr.success(response.success);
                        // Cập nhật trạng thái checkbox
                        $(`tr[data-user-id="${userId}"] .toggle-active`).bootstrapToggle('setState', response.is_active === 1);
                    } else {
                        toastr.error(response.error || 'Lỗi khi thay đổi trạng thái!');
                        // Hoàn tác trạng thái checkbox
                        $(`tr[data-user-id="${userId}"] .toggle-active`).bootstrapToggle('toggle');
                    }
                },
                error: function(xhr) {
                    console.log('Toggle AJAX error:', xhr.responseText);
                    toastr.error('Lỗi khi thay đổi trạng thái!');
                    // Hoàn tác trạng thái checkbox
                    $(`tr[data-user-id="${userId}"] .toggle-active`).bootstrapToggle('toggle');
                }
            });
        } else {
            // Hoàn tác trạng thái checkbox nếu hủy
            $(this).bootstrapToggle('toggle');
        }
    });

    // Xử lý xóa nhân viên
    $(document).on('click', '.delete-employee-btn', function() {
        var userId = $(this).data('user-id');
        console.log('Delete employee button clicked, userId:', userId);
        
        if (confirm('Bạn có chắc chắn muốn xóa nhân viên này? Hành động này không thể hoàn tác!')) {
            $.ajax({
                url: '/admin_delete_employee',
                type: 'POST',
                data: { user_id: userId },
                success: function(response) {
                    console.log('Delete AJAX success:', response);
                    if (response.success) {
                        toastr.success(response.success);
                        $(`tr[data-user-id="${userId}"]`).remove(); // Xóa hàng khỏi bảng
                        $('#employees-table').DataTable().row(`tr[data-user-id="${userId}"]`).remove().draw(); // Cập nhật DataTables
                    } else {
                        toastr.error(response.error || 'Lỗi khi xóa nhân viên!');
                    }
                },
                error: function(xhr) {
                    console.log('Delete AJAX error:', xhr.responseText);
                    toastr.error('Lỗi khi xóa nhân viên!');
                }
            });
        }
    });
});