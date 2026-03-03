/**
 * tab-nav.js - Tab navigation for switching between Planeter and Stjärnkarta panels.
 *
 * Implements the WAI-ARIA tabs pattern (automatic-activation model):
 *   https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
 *
 * HTML contract (IDs must exist in the DOM before instantiation):
 *   #tabNav        - <div role="tablist"> container
 *   #tabPlaneter   - tab button for the Planeter panel
 *   #tabSkyMap     - tab button for the Stjärnkarta panel
 *   #panelPlaneter - <div role="tabpanel"> for Planeter content
 *   #panelSkyMap   - <div role="tabpanel"> for Stjärnkarta content
 *
 * The HTML is responsible for setting the initial aria-* attributes, the
 * tab-panel--hidden class on the inactive panel, and the roving tabindex
 * values (tabindex="0" on the active tab, tabindex="-1" on the inactive tab).
 * This class activates the default tab ('planeter') on instantiation.
 *
 * Dispatches a 'tabChanged' CustomEvent on window with detail: { tabId }
 * whenever the active tab changes due to user interaction (click or keyboard).
 * The event is NOT dispatched during construction or when the already-active
 * tab is activated again.
 */

export class TabNav {
    constructor() {
        // Locate all required DOM elements once at construction time.
        this.nav = document.getElementById('tabNav');
        this.tabPlaneter = document.getElementById('tabPlaneter');
        this.tabSkyMap = document.getElementById('tabSkyMap');
        this.panelPlaneter = document.getElementById('panelPlaneter');
        this.panelSkyMap = document.getElementById('panelSkyMap');

        // Ordered list used for keyboard navigation (Home / End / ArrowLeft / ArrowRight).
        this.tabs = [this.tabPlaneter, this.tabSkyMap];

        // Track the currently active tab ID to suppress duplicate events.
        this._activeTabId = null;

        this._bindEvents();

        // Activate the default tab to ensure a consistent initial state.
        // Pass fromUser=false so no 'tabChanged' event is dispatched during setup.
        this.activateTab('planeter', false);
    }

    /**
     * Activate a tab panel and update all related ARIA state, CSS classes,
     * and roving tabindex values.
     *
     * @param {'planeter'|'skymap'} tabId - The tab to make active.
     * @param {boolean} [fromUser=true] - Whether the call originates from user interaction.
     *   Pass false during construction to suppress the 'tabChanged' event.
     */
    activateTab(tabId, fromUser = true) {
        const isPlaneter = tabId === 'planeter';

        // Sync aria-selected and active CSS class on both tab buttons.
        this.tabPlaneter.setAttribute('aria-selected', isPlaneter ? 'true' : 'false');
        this.tabSkyMap.setAttribute('aria-selected', isPlaneter ? 'false' : 'true');

        this.tabPlaneter.classList.toggle('tab-nav__tab--active', isPlaneter);
        this.tabSkyMap.classList.toggle('tab-nav__tab--active', !isPlaneter);

        // Roving tabindex: the active tab is reachable via Tab; inactive tab is skipped.
        this.tabPlaneter.setAttribute('tabindex', isPlaneter ? '0' : '-1');
        this.tabSkyMap.setAttribute('tabindex', isPlaneter ? '-1' : '0');

        // Show the active panel; hide the other.
        this.panelPlaneter.classList.toggle('tab-panel--hidden', !isPlaneter);
        this.panelSkyMap.classList.toggle('tab-panel--hidden', isPlaneter);

        // Notify other parts of the application that the active tab has changed,
        // but only when triggered by the user and only when the tab actually changed.
        if (fromUser && tabId !== this._activeTabId) {
            window.dispatchEvent(new CustomEvent('tabChanged', { detail: { tabId } }));
        }

        this._activeTabId = tabId;
    }

    /**
     * Attach click and keyboard event listeners.
     *
     * Keyboard navigation follows the WAI-ARIA tabs automatic-activation pattern:
     *   ArrowLeft  - move focus to the previous tab and activate it (wraps around)
     *   ArrowRight - move focus to the next tab and activate it (wraps around)
     *   Home       - move focus to the first tab and activate it
     *   End        - move focus to the last tab and activate it
     */
    _bindEvents() {
        this.tabPlaneter.addEventListener('click', () => this.activateTab('planeter'));
        this.tabSkyMap.addEventListener('click', () => this.activateTab('skymap'));

        this.nav.addEventListener('keydown', (event) => {
            const currentIndex = this.tabs.indexOf(document.activeElement);
            if (currentIndex === -1) return;

            let targetIndex = null;

            switch (event.key) {
                case 'ArrowLeft':
                    targetIndex = (currentIndex - 1 + this.tabs.length) % this.tabs.length;
                    break;
                case 'ArrowRight':
                    targetIndex = (currentIndex + 1) % this.tabs.length;
                    break;
                case 'Home':
                    targetIndex = 0;
                    break;
                case 'End':
                    targetIndex = this.tabs.length - 1;
                    break;
                default:
                    return;
            }

            event.preventDefault();
            const targetTab = this.tabs[targetIndex];
            targetTab.focus();
            // Automatic-activation: moving focus also activates the tab.
            const targetTabId = targetTab.dataset.tab;
            this.activateTab(targetTabId);
        });
    }
}
