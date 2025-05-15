document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const preview = document.getElementById('preview');
    const photoData = document.getElementById('photo_data');
    const captureButton = document.getElementById('capture');
    const submitButton = document.getElementById('submit');

    // Kiểm tra canvas
    if (!canvas || !canvas.getContext) {
        console.error('Canvas không được hỗ trợ hoặc không tìm thấy');
        alert('Trình duyệt không hỗ trợ canvas. Vui lòng thử trình duyệt khác.');
        return;
    }

    // Truy cập webcam
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
            console.log('Webcam stream khởi tạo thành công');
        })
        .catch(err => {
            console.error('Lỗi truy cập webcam:', err);
            alert('Không thể truy cập webcam. Vui lòng kiểm tra quyền truy cập.');
        });

    // Chụp và nén ảnh
    captureButton.addEventListener('click', function() {
        console.log('Bắt đầu chụp ảnh');
        if (!video.videoWidth || !video.videoHeight) {
            console.error('Video stream chưa sẵn sàng');
            alert('Webcam chưa sẵn sàng. Vui lòng thử lại.');
            return;
        }

        // Giảm kích thước canvas để giảm độ phân giải
        const maxWidth = 640;
        const maxHeight = 480;
        let width = video.videoWidth;
        let height = video.videoHeight;

        // Tính tỷ lệ để giữ nguyên tỷ lệ khung hình
        if (width > maxWidth || height > maxHeight) {
            const ratio = Math.min(maxWidth / width, maxHeight / height);
            width = width * ratio;
            height = height * ratio;
        }

        canvas.width = width;
        canvas.height = height;
        canvas.getContext('2d').drawImage(video, 0, 0, width, height);

        // Nén ảnh với chất lượng 0.7 (70%)
        const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
        console.log('Ảnh chụp:', dataUrl.substring(0, 50));
        preview.src = dataUrl;
        preview.style.display = 'block';
        photoData.value = dataUrl;
        submitButton.disabled = false;
    });
});