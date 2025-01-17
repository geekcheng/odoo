/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { onMounted, onWillUnmount } = owl.hooks;

export class MessagingMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        /**
         * global JS generated ID for this component. Useful to provide a
         * custom class to autocomplete input, so that click in an autocomplete
         * item is not considered as a click away from messaging menu in mobile.
         */
        this.id = _.uniqueId('o_messagingMenu_');

        // bind since passed as props
        this._onMobileNewMessageInputSelect = this._onMobileNewMessageInputSelect.bind(this);
        this._onMobileNewMessageInputSource = this._onMobileNewMessageInputSource.bind(this);
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        this._onHideMobileNewMessage = this._onHideMobileNewMessage.bind(this);
        this._onSelectMobileNavbarTab = this._onSelectMobileNavbarTab.bind(this);
        // for now, the legacy env is needed for internal functions such as
        // `useModels` to work
        this.env = owl.Component.env;
        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    _willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging_menu}
     */
    get messagingMenu() {
        return this.messaging && this.messaging.messagingMenu;
    }

    /**
     * @returns {string}
     */
    get mobileNewMessageInputPlaceholder() {
        return this.env._t("Search user...");
    }

    /**
     * @returns {Object[]}
     */
    get tabs() {
        return [{
            icon: 'fa fa-envelope',
            id: 'all',
            label: this.env._t("All"),
        }, {
            icon: 'fa fa-user',
            id: 'chat',
            label: this.env._t("Chat"),
        }, {
            icon: 'fa fa-users',
            id: 'channel',
            label: this.env._t("Channel"),
        }];
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Closes the menu when clicking outside, if appropriate.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (!this.messagingMenu) {
            return;
        }
        // ignore click inside the menu
        if (!this.root.el || this.root.el.contains(ev.target)) {
            return;
        }
        // in all other cases: close the messaging menu when clicking outside
        this.messagingMenu.close();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDesktopTabButton(ev) {
        this.messagingMenu.update({ activeTabId: ev.currentTarget.dataset.tabId });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNewMessage(ev) {
        if (!this.messaging.device.isMobile) {
            this.messaging.chatWindowManager.openNewMessage();
            this.messagingMenu.close();
        } else {
            this.messagingMenu.toggleMobileNewMessage();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggler(ev) {
        // avoid following dummy href
        ev.preventDefault();
        if (!this.messagingMenu) {
            return;
        }
        this.messagingMenu.toggleOpen();
    }

    /**
     * @private
     */
    _onHideMobileNewMessage() {
        this.messagingMenu.toggleMobileNewMessage();
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileNewMessageInputSelect(ev, ui) {
        this.messaging.openChat({ partnerId: ui.item.id });
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileNewMessageInputSource(req, res) {
        const value = _.escape(req.term);
        this.messaging.models['mail.partner'].imSearch({
            callback: partners => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: partner.nameOrDisplayName,
                        label: partner.nameOrDisplayName,
                    };
                });
                res(_.sortBy(suggestions, 'label'));
            },
            keyword: value,
            limit: 10,
        });
    }

    /**
     * @private
     * @param {Object} detail
     * @param {string} detail.tabId
     */
    _onSelectMobileNavbarTab(detail) {
        this.messagingMenu.update({ activeTabId: detail.tabId });
    }

}

Object.assign(MessagingMenu, {
    props: {},
    template: 'mail.MessagingMenu',
});

registerMessagingComponent(MessagingMenu);
