const ws = new WebSocket(`ws://${window.location.host}`);

function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}

let lastFile;
let curItem;

function debounce(func, delay) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    const fileSelect = document.getElementById('log-files');
    const logContent = document.getElementById('log-content');

    if (data.type === 'fileList') {
        while (fileSelect.firstChild) {
            fileSelect.removeChild(fileSelect.firstChild);
        }

        const fragment = document.createDocumentFragment();
        data.files.forEach(file => {
            const option = document.createElement('li');
            option.dataset.file = file;
            option.textContent = file.replace('.log', '');
            fragment.appendChild(option);
        });

        fileSelect.appendChild(fragment);
        lastFile = data.files[0];

        SetActions()
    } else if (data.file) {
        if (curItem.dataset.file === data.file) {
            logContent.textContent = data.content;

            const consoleEl = document.getElementById('console');
            if (consoleEl.scrollTop > consoleEl.scrollHeight / 1.5) {
                consoleEl.scrollTop += consoleEl.scrollHeight;
            }
            
            UpdateScroll()
        }
    }
};

function SetActions() {
    const logItems = document.querySelectorAll('#log-files li');
    const consoleEl = document.getElementById('console');
    
    logItems.forEach(item => {
        item.addEventListener('click', debounce((event) => {        
            if (curItem) {
                curItem.style.backgroundColor = ''
            }

            curItem = item

            ws.send(JSON.stringify({ action: 'selectFile', file: item.dataset.file }));

            item.style.backgroundColor = '#c9c9c9'
            setTimeout(() => { consoleEl.scrollTop += consoleEl.scrollHeight }, 500);
        }, 200));
    });
};

function UpdateScroll() {
    const c = document.getElementById('console');
    const s = document.getElementsByClassName("downscroll")

    c.addEventListener("scroll", (event) => {
        if (c.scrollTop < c.scrollHeight - 900) {
            s[0].style.opacity = 1
        } else {
            s[0].style.opacity = 0
        }
    });

    s[0].addEventListener("click", (event) => {
        c.scrollTop += c.scrollHeight
    })
}