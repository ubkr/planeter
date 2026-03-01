class TooltipManager {
    constructor() {
        this.tooltipEl = null;
        this.showTimer = null;
        this.activeIcon = null;
        this.showDelay = 300;
        this.offset = 10;
        this.viewportPadding = 8;

        this.handleMouseOver = this.handleMouseOver.bind(this);
        this.handleMouseOut = this.handleMouseOut.bind(this);
        this.handleFocusIn = this.handleFocusIn.bind(this);
        this.handleFocusOut = this.handleFocusOut.bind(this);
        this.handleEscape = this.handleEscape.bind(this);
        this.handleViewportChange = this.handleViewportChange.bind(this);
    }

    init() {
        this.ensureTooltip();

        document.addEventListener('mouseover', this.handleMouseOver);
        document.addEventListener('mouseout', this.handleMouseOut);
        document.addEventListener('focusin', this.handleFocusIn);
        document.addEventListener('focusout', this.handleFocusOut);
        document.addEventListener('keydown', this.handleEscape);
        window.addEventListener('resize', this.handleViewportChange);
        window.addEventListener('scroll', this.handleViewportChange, true);
    }

    ensureTooltip() {
        if (this.tooltipEl) {
            return;
        }

        this.tooltipEl = document.createElement('div');
        this.tooltipEl.className = 'tooltip';
        this.tooltipEl.setAttribute('role', 'tooltip');
        this.tooltipEl.setAttribute('aria-hidden', 'true');
        this.tooltipEl.id = 'custom-info-tooltip';

        document.body.appendChild(this.tooltipEl);
    }

    handleMouseOver(event) {
        const icon = event.target.closest('.info-icon');
        if (!icon) {
            return;
        }

        if (event.relatedTarget && icon.contains(event.relatedTarget)) {
            return;
        }

        this.scheduleShow(icon);
    }

    handleMouseOut(event) {
        const icon = event.target.closest('.info-icon');
        if (!icon) {
            return;
        }

        if (event.relatedTarget && icon.contains(event.relatedTarget)) {
            return;
        }

        this.hide(icon);
    }

    handleFocusIn(event) {
        const icon = event.target.closest('.info-icon');
        if (!icon) {
            return;
        }

        this.scheduleShow(icon);
    }

    handleFocusOut(event) {
        const icon = event.target.closest('.info-icon');
        if (!icon) {
            return;
        }

        this.hide(icon);
    }

    handleEscape(event) {
        if (event.key === 'Escape') {
            this.hide();
        }
    }

    handleViewportChange() {
        if (!this.activeIcon || !this.isVisible()) {
            return;
        }

        this.positionTooltip(this.activeIcon);
    }

    scheduleShow(icon) {
        const text = icon.getAttribute('title') || icon.dataset.tooltipTitle;
        if (!text) {
            return;
        }

        this.clearShowTimer();

        if (!icon.dataset.tooltipTitle) {
            icon.dataset.tooltipTitle = text;
        }

        icon.removeAttribute('title');

        this.showTimer = window.setTimeout(() => {
            this.show(icon, icon.dataset.tooltipTitle);
        }, this.showDelay);
    }

    show(icon, text) {
        if (!text) {
            return;
        }

        this.ensureTooltip();

        if (this.activeIcon && this.activeIcon !== icon) {
            this.restoreTitle(this.activeIcon);
            this.activeIcon.removeAttribute('aria-describedby');
        }

        this.activeIcon = icon;
        this.tooltipEl.textContent = text;
        this.tooltipEl.classList.add('is-visible');
        this.tooltipEl.setAttribute('aria-hidden', 'false');

        icon.setAttribute('aria-describedby', this.tooltipEl.id);

        this.positionTooltip(icon);
    }

    hide(icon = null) {
        this.clearShowTimer();

        if (icon) {
            this.restoreTitle(icon);
            icon.removeAttribute('aria-describedby');
        }

        if (this.activeIcon) {
            this.restoreTitle(this.activeIcon);
            this.activeIcon.removeAttribute('aria-describedby');
            this.activeIcon = null;
        }

        if (!this.tooltipEl) {
            return;
        }

        this.tooltipEl.classList.remove('is-visible');
        this.tooltipEl.setAttribute('aria-hidden', 'true');
    }

    restoreTitle(icon) {
        if (!icon || !icon.dataset.tooltipTitle) {
            return;
        }

        if (!icon.hasAttribute('title')) {
            icon.setAttribute('title', icon.dataset.tooltipTitle);
        }
    }

    positionTooltip(icon) {
        const iconRect = icon.getBoundingClientRect();

        this.tooltipEl.style.left = '0px';
        this.tooltipEl.style.top = '0px';

        const tooltipRect = this.tooltipEl.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        let left = iconRect.left + (iconRect.width / 2) - (tooltipRect.width / 2);
        let top = iconRect.top - tooltipRect.height - this.offset;

        if (top < this.viewportPadding) {
            top = iconRect.bottom + this.offset;
        }

        if (left < this.viewportPadding) {
            left = this.viewportPadding;
        }

        if (left + tooltipRect.width > viewportWidth - this.viewportPadding) {
            left = viewportWidth - tooltipRect.width - this.viewportPadding;
        }

        if (top + tooltipRect.height > viewportHeight - this.viewportPadding) {
            top = viewportHeight - tooltipRect.height - this.viewportPadding;
        }

        if (top < this.viewportPadding) {
            top = this.viewportPadding;
        }

        this.tooltipEl.style.left = `${Math.round(left)}px`;
        this.tooltipEl.style.top = `${Math.round(top)}px`;
    }

    clearShowTimer() {
        if (!this.showTimer) {
            return;
        }

        window.clearTimeout(this.showTimer);
        this.showTimer = null;
    }

    isVisible() {
        return this.tooltipEl && this.tooltipEl.classList.contains('is-visible');
    }
}

const tooltipManager = new TooltipManager();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => tooltipManager.init());
} else {
    tooltipManager.init();
}
