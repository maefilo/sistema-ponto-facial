// =============================================
// GLOBAL STATE
// =============================================
let currentPage = 'home';
let mainCamera = null;
let faceCamera = null;
let currentClassId = null;
let adminToken = localStorage.getItem('adminToken');
let adminData = null;
let loginCamera = null;

// =============================================
// NAVIGATION
// =============================================
function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const pageEl = document.getElementById(`page-${page}`);
    const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);

    if (pageEl) pageEl.classList.add('active');
    if (navEl) navEl.classList.add('active');

    const titles = {
        home: 'Início',
        recognize: 'Reconhecer',
        register: 'Cadastrar',
        students: 'Alunos',
        classes: 'Turmas',
        attendance: 'Presenças',
        settings: 'Configurações',
    };
    document.getElementById('pageTitle').textContent = titles[page] || page;

    currentPage = page;
    closeSidebar();

    // Start/stop cameras
    if (page === 'recognize') {
        startMainCamera();
    } else {
        stopMainCamera();
    }

    // Load page data
    loadPageData(page);
}

async function loadPageData(page) {
    switch (page) {
        case 'home':
            await loadStats();
            await loadRecentAttendances();
            break;
        case 'register':
            await loadStudentSelect();
            break;
        case 'students':
            await loadStudents();
            break;
        case 'classes':
            await loadClasses();
            break;
        case 'attendance':
            await loadAttendances();
            break;
        case 'settings':
            await loadSettings();
            await loadWhatsAppSettings();
            break;
    }
}

// =============================================
// SIDEBAR
// =============================================
function openSidebar() {
    document.getElementById('sidebar').classList.add('open');
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
}

// =============================================
// TOAST NOTIFICATIONS
// =============================================
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    toastMessage.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// =============================================
// API STATUS
// =============================================
async function checkApiStatus() {
    const health = await api.healthCheck();
    const dot = document.querySelector('.status-dot');
    const text = document.querySelector('.status-text');
    const settingsStatus = document.getElementById('settingsApiStatus');
    const facesCount = document.getElementById('facesRegistered');

    if (health.online) {
        dot.classList.add('online');
        text.textContent = 'Online';
        if (settingsStatus) settingsStatus.textContent = 'Online';
        if (facesCount) facesCount.textContent = health.faces_registered || 0;
    } else {
        dot.classList.remove('online');
        text.textContent = 'Offline';
        if (settingsStatus) settingsStatus.textContent = 'Offline';
    }
}

// =============================================
// HOME PAGE
// =============================================
async function loadStats() {
    try {
        const stats = await api.getStats();
        document.getElementById('statTotal').textContent = stats.total_students;
        document.getElementById('statPresent').textContent = stats.present_today;
        document.getElementById('statAbsent').textContent = stats.absent_today;
        document.getElementById('statRate').textContent = `${stats.attendance_rate}%`;
    } catch {
        console.log('Stats not available');
    }
}

async function loadRecentAttendances() {
    try {
        const attendances = await api.listAttendances({ limit: 5 });
        const container = document.getElementById('recentAttendances');

        if (attendances.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhuma presença registrada hoje</p>';
            return;
        }

        container.innerHTML = attendances.map(att => `
            <div class="recent-item">
                <div class="recent-avatar">${att.student_name.charAt(0).toUpperCase()}</div>
                <div class="recent-info">
                    <div class="recent-name">${att.student_name}</div>
                    <div class="recent-time">${new Date(att.date).toLocaleString('pt-BR')}</div>
                </div>
                <span class="recent-status status-${att.status}">
                    ${att.status === 'present' ? 'Presente' : 'Atrasado'}
                </span>
            </div>
        `).join('');
    } catch {
        console.log('Attendances not available');
    }
}

// =============================================
// RECOGNIZE PAGE
// =============================================
async function startMainCamera() {
    if (!mainCamera) {
        mainCamera = new CameraManager(
            document.getElementById('cameraFeed'),
            document.getElementById('cameraCanvas')
        );
    }
    await mainCamera.start();
}

function stopMainCamera() {
    if (mainCamera) {
        mainCamera.stop();
    }
}

async function handleRecognize() {
    const resultContainer = document.getElementById('recognizeResult');
    const resultCard = document.getElementById('resultCard');
    const captureBtn = document.getElementById('captureBtn');

    captureBtn.disabled = true;
    captureBtn.textContent = 'Processando...';

    try {
        const blob = await mainCamera.capture();
        if (!blob) {
            showToast('Erro ao capturar imagem', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', blob, 'photo.jpg');

        const result = await api.recognize(formData);

        resultContainer.style.display = 'block';
        const icon = document.getElementById('resultIcon');
        const title = document.getElementById('resultTitle');
        const message = document.getElementById('resultMessage');
        const details = document.getElementById('resultDetails');

        if (result.success) {
            resultCard.className = 'result-card success';
            icon.textContent = '✓';
            title.textContent = 'Presença Registrada!';
            message.textContent = result.message;
            details.innerHTML = `
                <p><strong>Nome:</strong> ${result.student.name}</p>
                <p><strong>Matrícula:</strong> ${result.student.registration_number}</p>
                <p><strong>Confiança:</strong> ${(result.confidence * 100).toFixed(1)}%</p>
            `;
            showToast('Presença registrada com sucesso!', 'success');
        } else {
            resultCard.className = 'result-card error';
            icon.textContent = '✗';
            title.textContent = 'Não Reconhecido';
            message.textContent = result.message;
            details.innerHTML = '';
            showToast(result.message, 'error');
        }
    } catch (err) {
        showToast('Erro ao reconhecer rosto', 'error');
    } finally {
        captureBtn.disabled = false;
        captureBtn.innerHTML = '<span>📸</span> Capturar e Reconhecer';
    }
}

// =============================================
// REGISTER PAGE
// =============================================
async function loadStudentSelect() {
    try {
        const students = await api.listStudents();
        const select = document.getElementById('faceStudentSelect');
        select.innerHTML = '<option value="">Selecione um aluno...</option>' +
            students.map(s => `<option value="${s.id}">${s.name} (${s.registration_number})</option>`).join('');
    } catch {
        console.log('Could not load students');
    }
}

async function handleRegisterStudent(e) {
    e.preventDefault();

    const data = {
        name: document.getElementById('regName').value,
        registration_number: document.getElementById('regMatricula').value,
        phone: document.getElementById('regPhone').value,
        email: document.getElementById('regEmail').value || null,
        parent_phone: document.getElementById('regParentPhone').value || null,
    };

    try {
        await api.createStudent(data);
        showToast('Aluno cadastrado com sucesso!', 'success');
        document.getElementById('registerForm').reset();
        await loadStudentSelect();
    } catch (err) {
        showToast(err.data?.detail || 'Erro ao cadastrar aluno', 'error');
    }
}

async function handleRegisterFace() {
    const studentId = document.getElementById('faceStudentSelect').value;
    if (!studentId) {
        showToast('Selecione um aluno', 'error');
        return;
    }

    if (!faceCamera) {
        faceCamera = new CameraManager(
            document.getElementById('faceCameraFeed'),
            document.getElementById('faceCameraCanvas')
        );
    }

    const started = await faceCamera.start();
    if (!started) {
        showToast('Erro ao acessar câmera', 'error');
        return;
    }

    // Wait a moment for camera to adjust
    await new Promise(r => setTimeout(r, 1000));

    const blob = await faceCamera.capture();
    if (!blob) {
        showToast('Erro ao capturar imagem', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', blob, 'face.jpg');

    try {
        await api.registerFace(studentId, formData);
        showToast('Rosto registrado com sucesso!', 'success');
    } catch (err) {
        showToast(err.data?.detail || 'Erro ao registrar rosto', 'error');
    }
}

// =============================================
// STUDENTS PAGE
// =============================================
async function loadStudents() {
    try {
        const students = await api.listStudents();
        const container = document.getElementById('studentsList');
        document.getElementById('studentCount').textContent = `${students.length} aluno(s)`;

        if (students.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhum aluno cadastrado</p>';
            return;
        }

        container.innerHTML = students.map(s => `
            <div class="student-card" data-name="${s.name.toLowerCase()}">
                <div class="student-avatar">${s.name.charAt(0).toUpperCase()}</div>
                <div class="student-info">
                    <div class="student-name">${s.name}</div>
                    <div class="student-detail">Matrícula: ${s.registration_number}</div>
                    <div class="student-detail">Telefone: ${s.phone}</div>
                </div>
                <div class="student-actions">
                    <button class="btn btn-danger" onclick="handleDeleteStudent(${s.id}, '${s.name.replace(/'/g, "\\'")}')">
                        Remover
                    </button>
                </div>
            </div>
        `).join('');
    } catch {
        showToast('Erro ao carregar alunos', 'error');
    }
}

async function handleDeleteStudent(id, name) {
    if (!confirm(`Remover aluno ${name}?`)) return;

    try {
        await api.deleteStudent(id);
        showToast('Aluno removido', 'success');
        await loadStudents();
    } catch {
        showToast('Erro ao remover aluno', 'error');
    }
}

function filterStudents(query) {
    const cards = document.querySelectorAll('.student-card');
    const lower = query.toLowerCase();
    cards.forEach(card => {
        const name = card.dataset.name;
        card.style.display = name.includes(lower) ? '' : 'none';
    });
}

// =============================================
// ATTENDANCE PAGE
// =============================================
async function loadAttendances() {
    const date = document.getElementById('attendanceDate').value;
    try {
        const params = {};
        if (date) params.date = date;

        const attendances = await api.listAttendances(params);
        const container = document.getElementById('attendanceList');

        if (attendances.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhuma presença encontrada</p>';
            return;
        }

        container.innerHTML = attendances.map(att => `
            <div class="attendance-item">
                <div class="recent-avatar">${att.student_name.charAt(0).toUpperCase()}</div>
                <div class="recent-info">
                    <div class="recent-name">${att.student_name}</div>
                    <div class="recent-time">${new Date(att.date).toLocaleString('pt-BR')}</div>
                </div>
                <span class="recent-status status-${att.status}">
                    ${att.status === 'present' ? 'Presente' : 'Atrasado'}
                </span>
            </div>
        `).join('');
    } catch {
        showToast('Erro ao carregar presenças', 'error');
    }
}

// =============================================
// SETTINGS PAGE
// =============================================
async function loadWhatsAppSettings() {
    const whatsappStatus = await api.getWhatsAppStatus();
    const statusEl = document.getElementById('whatsappStatus');
    const qrContainer = document.getElementById('whatsappQR');
    const qrImage = document.getElementById('qrImage');

    if (whatsappStatus.status === 'connected') {
        statusEl.textContent = 'Conectado';
        statusEl.style.color = '#059669';
        qrContainer.style.display = 'none';
    } else if (whatsappStatus.status === 'qr_needed') {
        statusEl.textContent = 'Aguardando QR Code';
        statusEl.style.color = '#f59e0b';
        if (whatsappStatus.qr) {
            qrContainer.style.display = 'block';
            qrImage.src = whatsappStatus.qr;
        }
    } else {
        statusEl.textContent = 'Desconectado';
        statusEl.style.color = '#dc2626';
        qrContainer.style.display = 'none';
    }
}

async function handleSendNotification() {
    const studentId = document.getElementById('notifyStudent').value;
    const message = document.getElementById('notifyMessage').value;

    if (!studentId || !message) {
        showToast('Preencha todos os campos', 'error');
        return;
    }

    try {
        await api.sendNotification(parseInt(studentId), message);
        showToast('Notificação enviada!', 'success');
        document.getElementById('notifyStudent').value = '';
        document.getElementById('notifyMessage').value = '';
    } catch (err) {
        showToast(err.data?.detail || 'Erro ao enviar notificação', 'error');
    }
}

// =============================================
// CLASSES PAGE
// =============================================
async function loadClasses() {
    try {
        const classes = await api.listClasses();
        const container = document.getElementById('classesList');

        if (classes.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhuma turma cadastrada</p>';
            return;
        }

        container.innerHTML = classes.map(c => `
            <div class="student-card">
                <div class="student-avatar">🏫</div>
                <div class="student-info">
                    <div class="student-name">${c.name}</div>
                    <div class="student-detail">Horário: ${c.schedule || 'Não definido'}</div>
                    <div class="student-detail">${c.student_count} aluno(s)</div>
                </div>
                <div class="student-actions">
                    <button class="btn btn-primary" onclick="openClassModal(${c.id}, '${c.name.replace(/'/g, "\\'")}')">
                        Gerenciar
                    </button>
                    <button class="btn btn-danger" onclick="handleDeleteClass(${c.id}, '${c.name.replace(/'/g, "\\'")}')">
                        Remover
                    </button>
                </div>
            </div>
        `).join('');
    } catch {
        showToast('Erro ao carregar turmas', 'error');
    }
}

async function handleCreateClass(e) {
    e.preventDefault();

    const data = {
        name: document.getElementById('className').value,
        schedule: document.getElementById('classSchedule').value || null,
    };

    try {
        await api.createClass(data);
        showToast('Turma criada com sucesso!', 'success');
        document.getElementById('classForm').reset();
        await loadClasses();
    } catch (err) {
        showToast(err.data?.detail || 'Erro ao criar turma', 'error');
    }
}

async function handleDeleteClass(id, name) {
    if (!confirm(`Remover turma "${name}"?`)) return;

    try {
        await api.deleteClass(id);
        showToast('Turma removida', 'success');
        await loadClasses();
    } catch {
        showToast('Erro ao remover turma', 'error');
    }
}

async function openClassModal(classId, className) {
    currentClassId = classId;
    document.getElementById('modalClassName').textContent = className;
    document.getElementById('classModal').style.display = 'flex';

    await loadClassStudents();
    await loadModalStudentSelect();
}

function closeClassModal() {
    document.getElementById('classModal').style.display = 'none';
    currentClassId = null;
}

async function loadClassStudents() {
    try {
        const students = await api.listClassStudents(currentClassId);
        const container = document.getElementById('modalClassStudents');

        if (students.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhum aluno nesta turma</p>';
            return;
        }

        container.innerHTML = students.map(s => `
            <div class="recent-item">
                <div class="recent-avatar">${s.name.charAt(0).toUpperCase()}</div>
                <div class="recent-info">
                    <div class="recent-name">${s.name}</div>
                    <div class="recent-time">Matrícula: ${s.registration_number}</div>
                </div>
                <button class="btn btn-danger" onclick="handleRemoveStudentFromClass(${s.id})">
                    Remover
                </button>
            </div>
        `).join('');
    } catch {
        showToast('Erro ao carregar alunos da turma', 'error');
    }
}

async function loadModalStudentSelect() {
    try {
        const students = await api.listStudents();
        const select = document.getElementById('modalStudentSelect');
        select.innerHTML = '<option value="">Selecione um aluno...</option>' +
            students.map(s => `<option value="${s.id}">${s.name} (${s.registration_number})</option>`).join('');
    } catch {
        console.log('Could not load students');
    }
}

async function handleAddStudentToClass() {
    const studentId = document.getElementById('modalStudentSelect').value;
    if (!studentId) {
        showToast('Selecione um aluno', 'error');
        return;
    }

    try {
        await api.addStudentToClass(currentClassId, parseInt(studentId));
        showToast('Aluno adicionado à turma!', 'success');
        await loadClassStudents();
        await loadClasses();
    } catch (err) {
        showToast(err.data?.detail || 'Erro ao adicionar aluno', 'error');
    }
}

async function handleRemoveStudentFromClass(studentId) {
    if (!confirm('Remover aluno desta turma?')) return;

    try {
        await api.removeStudentFromClass(currentClassId, studentId);
        showToast('Aluno removido da turma', 'success');
        await loadClassStudents();
        await loadClasses();
    } catch {
        showToast('Erro ao remover aluno', 'error');
    }
}

// =============================================
// AUTH / LOGIN
// =============================================
function showLoginScreen() {
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('mainApp').style.display = 'none';
    startLoginCamera();
}

function showMainApp() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('mainApp').style.display = 'flex';
    if (loginCamera) loginCamera.stop();
    navigateTo('home');
}

async function startLoginCamera() {
    if (!loginCamera) {
        loginCamera = new CameraManager(
            document.getElementById('loginCameraFeed'),
            document.getElementById('loginCameraCanvas')
        );
    }
    await loginCamera.start();
}

async function handleLoginFace() {
    const btn = document.getElementById('loginFaceBtn');
    btn.disabled = true;
    btn.textContent = 'Reconhecendo...';

    try {
        const blob = await loginCamera.capture();
        if (!blob) {
            showToast('Erro ao capturar imagem', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', blob, 'login.jpg');

        const result = await api.loginFace(formData);
        adminToken = result.token;
        adminData = result.admin;
        localStorage.setItem('adminToken', adminToken);
        showToast(`Bem-vindo, ${result.admin.name}!`, 'success');
        showMainApp();
    } catch (err) {
        showToast(err.data?.detail || 'Rosto não reconhecido como admin', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>📸</span> Reconhecer e Entrar';
    }
}

async function handleLoginPassword(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const result = await api.loginAdmin({ email, password });
        adminToken = result.token;
        adminData = result.admin;
        localStorage.setItem('adminToken', adminToken);
        showToast(`Bem-vindo, ${result.admin.name}!`, 'success');
        showMainApp();
    } catch (err) {
        showToast(err.data?.detail || 'Credenciais inválidas', 'error');
    }
}

async function handleRegisterAdmin(e) {
    e.preventDefault();
    const name = document.getElementById('regAdminName').value;
    const email = document.getElementById('regAdminEmail').value;
    const password = document.getElementById('regAdminPassword').value;

    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', email);
    formData.append('password', password);

    const camera = new CameraManager(
        document.getElementById('adminFaceCameraFeed'),
        document.getElementById('adminFaceCameraCanvas')
    );

    const started = await camera.start();
    if (!started) {
        showToast('Acesso à câmera necessário para registrar rosto', 'error');
        return;
    }

    await new Promise(r => setTimeout(r, 1000));
    const blob = await camera.capture();
    camera.stop();

    if (!blob) {
        showToast('Erro ao capturar imagem', 'error');
        return;
    }

    formData.append('file', blob, 'admin_face.jpg');

    try {
        const result = await api.registerAdmin(formData);
        adminToken = result.token;
        adminData = result.admin;
        localStorage.setItem('adminToken', adminToken);
        showToast('Admin cadastrado e rosto registrado!', 'success');
        showMainApp();
    } catch (err) {
        showToast(err.data?.detail || 'Erro ao cadastrar admin', 'error');
    }
}

function handleLogout() {
    adminToken = null;
    adminData = null;
    localStorage.removeItem('adminToken');
    showToast('Logout realizado', 'success');
    showLoginScreen();
}

async function checkAuth() {
    if (adminToken) {
        try {
            const result = await api.getMe(adminToken);
            adminData = result;
            showMainApp();
        } catch {
            adminToken = null;
            adminData = null;
            localStorage.removeItem('adminToken');
            showLoginScreen();
        }
    } else {
        showLoginScreen();
    }
}

function loadSettings() {
    if (adminData) {
        document.getElementById('adminName').textContent = adminData.name;
        document.getElementById('adminEmail').textContent = adminData.email;
    }
}

// =============================================
// INITIALIZATION
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    // Sidebar
    document.getElementById('openSidebar').addEventListener('click', openSidebar);
    document.getElementById('closeSidebar').addEventListener('click', closeSidebar);

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            navigateTo(item.dataset.page);
        });
    });

    // Recognize
    document.getElementById('captureBtn').addEventListener('click', handleRecognize);

    // Register form
    document.getElementById('registerForm').addEventListener('submit', handleRegisterStudent);
    document.getElementById('captureFaceBtn').addEventListener('click', handleRegisterFace);

    // Search students
    document.getElementById('searchStudents').addEventListener('input', (e) => {
        filterStudents(e.target.value);
    });

    // Attendance date filter
    document.getElementById('attendanceDate').addEventListener('change', loadAttendances);

    // Settings
    document.getElementById('sendNotifyBtn').addEventListener('click', handleSendNotification);

    // Classes
    document.getElementById('classForm').addEventListener('submit', handleCreateClass);

    // Login
    document.getElementById('loginFaceBtn').addEventListener('click', handleLoginFace);
    document.getElementById('loginForm').addEventListener('submit', handleLoginPassword);
    document.getElementById('registerAdminForm').addEventListener('submit', handleRegisterAdmin);

    // Login tabs
    document.getElementById('tabFace').addEventListener('click', () => {
        document.querySelectorAll('.login-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.login-tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById('tabFace').classList.add('active');
        document.getElementById('loginFaceContent').classList.add('active');
        startLoginCamera();
    });
    document.getElementById('tabPassword').addEventListener('click', () => {
        document.querySelectorAll('.login-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.login-tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById('tabPassword').classList.add('active');
        document.getElementById('loginPasswordContent').classList.add('active');
        if (loginCamera) loginCamera.stop();
    });

    // Show register admin form
    document.getElementById('showRegisterAdmin').addEventListener('click', () => {
        const faceContent = document.getElementById('loginFaceContent');
        const passContent = document.getElementById('loginPasswordContent');
        const regContent = document.getElementById('registerAdminContent');
        const showRegister = regContent.style.display === 'none';
        faceContent.style.display = 'none';
        passContent.style.display = 'none';
        regContent.style.display = showRegister ? 'block' : 'none';
        document.getElementById('showRegisterAdmin').textContent = showRegister ? 'Voltar ao login' : 'Cadastrar primeiro admin';
    });

    // Check API status
    checkApiStatus();
    setInterval(checkApiStatus, 30000);

    // Check auth and show appropriate screen
    checkAuth();

    // Register service worker for PWA
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('sw.js').catch(() => {});
    }
});
