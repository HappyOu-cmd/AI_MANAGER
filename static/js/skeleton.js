// Skeleton Loader System
class SkeletonLoader {
    static createLine(width = '100%', className = '') {
        const line = document.createElement('div');
        line.className = `skeleton skeleton-line ${className}`;
        line.style.width = width;
        return line;
    }

    static createCard(content = []) {
        const card = document.createElement('div');
        card.className = 'skeleton-card';
        
        if (content.length === 0) {
            // По умолчанию создаем несколько линий
            card.appendChild(this.createLine('100%'));
            card.appendChild(this.createLine('80%', 'short'));
            card.appendChild(this.createLine('60%', 'short'));
        } else {
            content.forEach(item => {
                if (typeof item === 'string') {
                    card.appendChild(this.createLine(item));
                } else {
                    card.appendChild(item);
                }
            });
        }
        
        return card;
    }

    static createCircle(size = '2.5rem') {
        const circle = document.createElement('div');
        circle.className = 'skeleton skeleton-circle';
        circle.style.width = size;
        circle.style.height = size;
        return circle;
    }

    static showSkeleton(container, type = 'card') {
        if (!container) return null;
        
        const skeleton = type === 'card' 
            ? this.createCard()
            : this.createLine();
        
        container.innerHTML = '';
        container.appendChild(skeleton);
        container.style.display = 'block';
        
        return skeleton;
    }

    static hideSkeleton(container) {
        if (!container) return;
        container.innerHTML = '';
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SkeletonLoader;
}

