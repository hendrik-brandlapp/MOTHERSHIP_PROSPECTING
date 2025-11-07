/**
 * Searchable Multi-Select Dropdown Component
 * Premium, Notion-style category filtering
 */

class SearchableDropdown {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = [];
        this.selected = new Set();
        this.excluded = new Set();
        this.onChange = options.onChange || (() => {});
        this.placeholder = options.placeholder || 'Select categories...';
        
        this.render();
    }
    
    setOptions(options) {
        this.options = options.sort();
        // Initialize all as included by default
        this.selected = new Set(options);
        this.excluded = new Set();
        this.renderSelectedTags();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="searchable-dropdown-wrapper">
                <div class="selected-tags" id="${this.container.id}-tags"></div>
                <div class="dropdown-trigger-modern" id="${this.container.id}-trigger">
                    <span class="trigger-text">${this.placeholder}</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="dropdown-menu-modern" id="${this.container.id}-menu">
                    <div class="dropdown-search-box">
                        <i class="fas fa-search"></i>
                        <input type="text" placeholder="Search categories..." id="${this.container.id}-search">
                    </div>
                    <div class="dropdown-options-list" id="${this.container.id}-options"></div>
                </div>
            </div>
        `;
        
        this.attachEvents();
    }
    
    attachEvents() {
        const trigger = document.getElementById(`${this.container.id}-trigger`);
        const menu = document.getElementById(`${this.container.id}-menu`);
        const search = document.getElementById(`${this.container.id}-search`);
        
        // Toggle dropdown
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('show');
            if (menu.classList.contains('show')) {
                search.focus();
            }
        });
        
        // Close on outside click
        document.addEventListener('click', () => {
            menu.classList.remove('show');
        });
        
        menu.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        // Search functionality
        search.addEventListener('input', (e) => {
            this.filterOptions(e.target.value);
        });
    }
    
    renderOptions(filter = '') {
        const optionsList = document.getElementById(`${this.container.id}-options`);
        const filtered = this.options.filter(opt => 
            opt.toLowerCase().includes(filter.toLowerCase())
        );
        
        optionsList.innerHTML = filtered.map(option => {
            const isIncluded = this.selected.has(option) && !this.excluded.has(option);
            const isExcluded = this.excluded.has(option);
            const state = isExcluded ? 'excluded' : (isIncluded ? 'included' : 'none');
            
            return `
                <div class="dropdown-option-item ${state}" data-option="${option}">
                    <div class="option-checkbox">
                        ${state === 'included' ? '<i class="fas fa-check-circle"></i>' : ''}
                        ${state === 'excluded' ? '<i class="fas fa-times-circle"></i>' : ''}
                        ${state === 'none' ? '<i class="far fa-circle"></i>' : ''}
                    </div>
                    <span class="option-label">${option}</span>
                </div>
            `;
        }).join('');
        
        // Attach click handlers
        optionsList.querySelectorAll('.dropdown-option-item').forEach(item => {
            item.addEventListener('click', () => {
                this.toggleOption(item.dataset.option);
            });
        });
    }
    
    filterOptions(searchTerm) {
        this.renderOptions(searchTerm);
    }
    
    toggleOption(option) {
        const isIncluded = this.selected.has(option) && !this.excluded.has(option);
        const isExcluded = this.excluded.has(option);
        
        if (isIncluded) {
            // included → excluded
            this.excluded.add(option);
        } else if (isExcluded) {
            // excluded → removed
            this.excluded.delete(option);
            this.selected.delete(option);
        } else {
            // removed → included
            this.selected.add(option);
            this.excluded.delete(option);
        }
        
        this.renderOptions();
        this.renderSelectedTags();
        this.onChange(this.getState());
    }
    
    renderSelectedTags() {
        const tagsContainer = document.getElementById(`${this.container.id}-tags`);
        const allTags = [];
        
        // Show included tags
        this.options.forEach(option => {
            const isIncluded = this.selected.has(option) && !this.excluded.has(option);
            const isExcluded = this.excluded.has(option);
            
            if (isIncluded || isExcluded) {
                allTags.push({option, state: isExcluded ? 'excluded' : 'included'});
            }
        });
        
        if (allTags.length === 0) {
            tagsContainer.innerHTML = '';
            return;
        }
        
        tagsContainer.innerHTML = allTags.map(({option, state}) => `
            <span class="selected-tag ${state}" data-option="${option}">
                <span>${option}</span>
                <i class="fas fa-times" onclick="categoryDropdown.toggleOption('${option}')"></i>
            </span>
        `).join('');
    }
    
    getState() {
        return {
            included: Array.from(this.selected).filter(opt => !this.excluded.has(opt)),
            excluded: Array.from(this.excluded)
        };
    }
}

