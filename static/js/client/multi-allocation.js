define("models/v2/externalAccount", ["underscore", "components/common/scripts/models/v2/baseModels"], function(e, t) {
        var n = {
                transaction_cheque_account: "Transaction / Cheque Account",
                savings_deposit_account: "Savings / Deposit Account",
                term_deposit_account: "Term Deposit Account",
                brokerage_account: "Brokerage Account",
                my_super: "MySuper",
                super_fund: "Super Fund",
                smsf: "SMSF"
            },
            r = {
                endpoint: "/external_accounts",
                isSpousal: function() {
                    return this.get("accountOwner") === "spouse"
                },
                isEmployerPlan: function() {
                    var t = ["401k", "roth_401k", "profit_sharing", "403b", "401a", "457b", "thrift_savings_plan"];
                    return e.contains(t, this.get("accountType"))
                },
                hashKey: function() {
                    return ["accountOwner", "accountType", "annualContributionCents", "balanceCents"].reduce(function(e, t) {
                        return e + t + ":" + this.get(t) + ";"
                    }.bind(this), "")
                },
                displayAccountType: function() {
                    return n[this.get("accountType")]
                }
            };
        r.validation = {
            institutionName: {
                required: !0
            },
            accountType: {
                required: !0
            },
            investmentType: {
                required: !0
            },
            accountOwner: {
                required: !0
            },
            balanceCents: {
                required: !0
            },
            annualContributionCents: {
                required: !0
            },
            advisorFeePercent: {
                range: [0, 100],
                required: !1
            }
        };
        var i = {
            VALID_ACCOUNT_TYPES: n
        };
        return t.RelationalModel.extend(r, i)
}),define("views/advice/multiAllocationModalView", ["jquery", "underscore", "common/betterment.views"], function($, _, n) {
    return n.ModalView.extend({
            template: "advice/confirmMultiAllocationChanges",
            className: "multi-allocation-modal",
            events: {
                "click .ok": "saveChanges",
                "click .cancel": "closeModal"
            },
            onInitialize: function(){
                this.changes =  this.options.multiAllocationController.getChanges();
            },
            onRender: function() {
                var i, row, market, m_size, currency_hedge;

                for(i in this.changes){
                    market = this.options.multiAllocationController.$regions_dict[this.changes[i].key];
                    m_size = parseInt(this.changes[i].size);
                    if(m_size==null || m_size==undefined){
                        m_size = "---"
                    }
                    else{
                          m_size = m_size  + "% ";
                    }
                    if(this.changes[i].currency_hedge_value==null || this.changes[i].currency_hedge_value==undefined){
                        currency_hedge = "---"
                    }
                    else {
                        currency_hedge = this.changes[i].currency_hedge_value ? "Yes" : "No";
                    }
                    row = '<tr><td>' + market + '</td><td>' + m_size + '</td><td>'  + currency_hedge + '</td></tr>';
                    this.$('tbody').append(row);
                }

            },
            saveChanges: function(){
                this.closeModal();
                this.options.multiAllocationController.save();

            },
            closeModal: function(){
                this.options.modal.close(this);
            },

            onShow: function() {}
        }
    );
}), define("components/portfolio/scripts/services/portfolioSetService", ["underscore", "components/portfolio/scripts/models/portfolioSet", "components/common/scripts/models/appData", "components/account/scripts/constants/accountTypes", "jquery"], function(e, t, n, r, jquery) {
        var i = {},
            s = {};
        //var _ = e;
        return {
            loadPortfolioSet: function(e) {
                var n = i[e],
                    r = s[e],
                    o = new $.Deferred;
                if (n) o.resolve(n);
                else {
                    var u = !!r;
                    u || (r = s[e] = new $.Deferred), r.done(function(e) {
                        o.resolve(e)
                    }).fail(function() {
                        o.reject()
                    }), u || (n =  t.findOrCreate({
                        id: e
                    }), n.fetch().done(function() {
                        i[e] = n, r.resolve(n)
                    }).fail(function() {
                        r.reject()
                    }))
                }
                return o.promise()
            },
            loadPortfolioSetForAccount: function(e) {
                var regions_dict = {
                     au: "Australia",
                     dm: "Developed Markets",
                     usa: "United States",
                     uk: "United Kingdom",
                     europe: "Europe",
                     japan: "Japan",
                     asia: "Asia (ex-Japan)",
                     china: "China",
                     em: "Emerging Markets"};
                var custom_size = 0;
                _.each(regions_dict, function(value, key){
                   custom_size = custom_size + e.get(key + "_size");

                }.bind(this));
                if(custom_size=0) {
                    return this.loadPortfolioSet(e.get("portfolioSetId"))
                }
                else{
                    var key = "goal_" + e.get("id") + "_" + e.get("portfolioSetId");
                    return this.loadPortfolioSet(key);
                }
            },
            getPortfolioSet: function(e) {
                return i[e];
            },
            deletePortfolioSet: function(key) {
                delete i[key];
                delete s[key];
            },
            getPortfolioSetForAccount: function(e) {
                 var regions_dict = {
                     au: "Australia",
                     dm: "Developed Markets",
                     usa: "United States",
                     uk: "United Kingdom",
                     europe: "Europe",
                     japan: "Japan",
                     asia: "Asia (ex-Japan)",
                     china: "China",
                     em: "Emerging Markets"};
                var custom_size = 0;
                _.each(regions_dict, function(value, key){
                   custom_size = custom_size + e.get(key + "_size");

                }.bind(this));
                if(custom_size=0) {
                    return this.getPortfolioSet(e.get("portfolioSetId"));
                }
                else{
                    var key = "goal_" + e.get("id") + "_" + e.get("portfolioSetId");
                    return i[key]
                }
            },
            getDefaultInvestingPortfolioSetId: function() {
                return n.getInstance().get("defaultPortfolioSetID")
            },
            getDefaultIraPortfolioSetId: function() {
                return n.getInstance().get("defaultIraPortfolioSetID")
            },
            getDefaultPortfolioSetId: function(e) {
                return r.isIRA(e) ? this.getDefaultIraPortfolioSetId() : this.getDefaultInvestingPortfolioSetId()
            }
        }
    }), define("views/advice/multiAllocationCardView", ["underscore", "common/slider", "services/allocationService", "common/betterment.views", "jquery", "tinyToggle"], function(_, slider, allocationService, bt, $, tinyToggle){
     return bt.View.extend({
         template: "advice/multiAllocationCard",
         events: {
                "click .open-lg": "openCard",
                "click .close-lg": "closeCard"
            },
         toolTips: {
                ".currency-help": {
                    position: {
                        my: "bottom center",
                        at: "top center"
                    }
                }
            },
         onInitialize: function(){
             this.size_slider_model = this.options.model_key + "_size";
             this.currency_hedge_model = this.options.model_key + "_currency_hedge";
         },
         onRender: function() {
                this.size_slider = this.createSlider();
                this.$(".region-name").text(this.options.title);
                this.currency_hedge_value = this.model.get(this.currency_hedge_model);

                this.hedge_toggle = this.$(".tiny-toggle").tinyToggle({onChange:  function(checkbox, value)  {
                    if(this.currency_hedge_value == value)return;
                    this.currency_hedge_value = value;
                    this.options.parent.hasChanged();
                }.bind(this),});

            },
         onShow: function() {
                if(this.currency_hedge_value){this.hedge_toggle.tinyToggle("check")};
                this.drawSize();
                if(this.size_slider_value>0){this.openCard();}
            },
         createSlider: function() {
                this.size_slider_value = this.model.num(this.size_slider_model)*100;
                this.drawSize();
                var e = this.slider('.size-slider', {
                    min: 0,
                    max: 100,
                    step: 1,
                    value: this.size_slider_value,
                    slide: function(e, t) {
                        var allocated = t.value - this.size_slider_value;
                        this.size_slider_value = t.value;
                        this.drawSize();
                        this.options.parent.resize(this.options.model_key, allocated);
                        this.options.parent.fixSize();
                        this.options.parent.hasChanged();
                    }.bind(this)
                });
                return e
            },
         hasChanged: function(){
             var changeObject = {has_changed: false, changes: {key:this.options.model_key}};

             if(Math.abs(this.size_slider_value - 100*this.model.num(this.size_slider_model)) > 1){
                 changeObject.has_changed = true;
                 changeObject.changes.size = this.size_slider_value;
             }

             if(this.currency_hedge_value != this.model.get(this.currency_hedge_model)) {
                 changeObject.has_changed = true;
                 changeObject.changes.currency_hedge_value = this.currency_hedge_value;
             }

             return changeObject
        },
         drawSize: function(){
              this.$(".size-pct").text(parseInt(this.size_slider_value) + "%");

         },
         reset: function(){

             this.size_slider_value = this.model.num(this.size_slider_model)*100;
             this.size_slider.slider("value", this.size_slider_value);
             this.currency_hedge_value = this.model.get(this.currency_hedge_model);
             if(this.currency_hedge_value){
                 this.hedge_toggle.tinyToggle("check");
             }
             else{
                 this.hedge_toggle.tinyToggle("uncheck");
             }
             this.drawSize();

         },
         save: function(){
             this.model.set(this.size_slider_model, this.size_slider_value/100);
             this.model.set(this.currency_hedge_model, this.currency_hedge_value);
         },
         openCard: function(e){
                var button = this.$('.open-lg');
                var card = this.$('.allocation-card');
                var content = card.find('.allocation-card-content');
                button.removeClass("open-lg");
                button.addClass("close-lg");
                content.removeClass("allocation-content-hide");
                content.addClass("allocation-content-show");
            },
         closeCard: function(e){
                var button = this.$(e.currentTarget);
                var card = button.parents('.allocation-card');
                var content = card.find('.allocation-card-content');
                button.removeClass("close-lg");
                button.addClass("open-lg");
                content.removeClass("allocation-content-show");
                content.addClass("allocation-content-hide");
            }


     });

 }),

 define("views/advice/multiAllocationView",
     ["underscore", "common/betterment.views", "views/advice/multiAllocationCardView", "components/portfolio/scripts/services/portfolioSetService", "views/advice/multiAllocationModalView"],
     function(_, bt, mac, pss, bsm) {
        return bt.View.extend({
            template: "advice/multiAllocation",
            events: {
                "click .ma-reset-all": "reset",
                "click .ma-set-all": "preSave"},
            onInitialize: function() {
                this.$regions_dict = {
                               au: "Australia",
                               dm: "Developed Markets",
                               usa: "United States",
                               uk: "United Kingdom",
                               europe: "Europe",
                               japan: "Japan",
                               asia: "Asia (ex-Japan)",
                               china: "China",
                               em: "Emerging Markets"};
                _.each(this.$regions_dict, function(value, key){
                    this.addRegion(key+"Region", "#" + key + "-region");

                }.bind(this));

            },
            onRender: function() {
                _.each(this.$regions_dict, function(value, key){
                    this.$("div#multiAllocationRegion").append("<div id='" + key + "-region'></div>");
                    this[key + "View"] = new mac({model:this.model, parent:this, model_key: key, title: value});
                    this[key + "Region"].show(this[key + "View"]);

                }.bind(this));
            },
            hasChanged: function(){
                this.changed = false;
                var buttons = this.$(".ma-save-buttons");

                 _.each(this.$regions_dict, function(value, key){
                    var changeObject = this[key + "View"].hasChanged();
                    this.changed = this.changed || changeObject.has_changed;
                }.bind(this));

                if(this.changed){
                    buttons.removeClass("ma-hide");
                    buttons.addClass("ma-show");
                }
                else{
                    buttons.removeClass("ma-show");
                    buttons.addClass("ma-hide");
                }

            },
            onShow: function() {
            },
            reset: function() {
                _.each(this.$regions_dict, function(value, key){
                    this[key + "View"].reset();
                }.bind(this));
                this.hasChanged();

            },
            getChanges: function(){
                var changes = [];
                _.each(this.$regions_dict, function(value, key){
                    var changeObject = this[key + "View"].hasChanged();
                    if(changeObject.has_changed) changes.push(changeObject.changes);
                }.bind(this));
                return changes;
            },
            fixSize: function(){
                var market = [];
                var total_size  = 0;
                _.each(this.$regions_dict, function(value, key){
                    var size_value = this[key + "View"].size_slider_value;
                    if(size_value == 0) return;
                    total_size += size_value;
                    market.push({key:key, size_value:size_value});
                }.bind(this));

                market = _.sortBy(market, function(o){ return o.size_value; });
                market.reverse();
                var dif  = 100-total_size;
                if (dif==0)return;

                this[market[0].key + "View"].size_slider_value += dif;
                this[market[0].key + "View"].size_slider.slider("value", this[market[0].key + "View"].size_slider_value);
                this[market[0].key + "View"].drawSize();
            },
            resize: function(allocated_key, allocated){
                var market = [];
                var default_key = "au";
                var left_allocation = 0;
                var allocation_from_custom;
                if(allocated_key=="au")default_key="dm";

                if(allocated<0){
                    this[default_key + "View"].size_slider_value = this[default_key + "View"].size_slider_value - allocated;
                    if(this[default_key + "View"].size_slider_value>1)this[default_key + "View"].size_slider_value=100;
                    this[default_key + "View"].size_slider.slider("value", this[default_key + "View"].size_slider_value);
                    this[default_key + "View"].drawSize();
                    this[default_key + "View"].openCard();
                    return;
                }

                if(this[default_key + "View"].size_slider_value>0){
                   var allocation_from_main =  this[default_key + "View"].size_slider_value - allocated;
                    if(allocation_from_main>=0){
                        left_allocation = 0;
                    }
                    else{
                        left_allocation = -1*allocation_from_main;
                        allocation_from_main = 0;
                    }

                    this[default_key + "View"].size_slider_value = allocation_from_main;
                    this[default_key + "View"].size_slider.slider("value", this[default_key + "View"].size_slider_value);
                    this[default_key + "View"].drawSize();

                    if(left_allocation==0)return;

                }
                else{
                    left_allocation = allocated;
                }

                _.each(this.$regions_dict, function(value, key){
                    if(key==allocated_key)return;
                    if(key==default_key)return;
                    var size_value = this[key + "View"].size_slider_value;
                    if(size_value == 0) return;
                    market.push({key:key, size_value:size_value});
                }.bind(this));

                market = _.sortBy(market, function(o){ return o.size_value; });
                market.reverse();

                for(var i in market){
                    allocation_from_custom =  this[market[i].key + "View"].size_slider_value - left_allocation;
                    if(allocation_from_custom>=0){
                        left_allocation = 0;
                    }
                    else{
                        left_allocation = -1*allocation_from_custom;
                        allocation_from_custom = 0;
                    }
                    this[market[i].key + "View"].size_slider_value = allocation_from_custom;
                    this[market[i].key + "View"].size_slider.slider("value", this[market[i].key + "View"].size_slider_value);
                    this[market[i].key + "View"].drawSize();

                    if(left_allocation==0)return;

                }
            },
            preSave:function(){
                var custom_size = 0;
                 _.each(this.$regions_dict, function(value, key){
                    custom_size = custom_size + this[key + "View"].size_slider_value;
                 }.bind(this));
                 if (custom_size!=100){
                     BMT.alert({
                        title: "Error",
                        body: "Your portfolio allocation currently exceeds 100%, please adjust the allocation amounts to set your revised allocation.",
                        icon: "error"
                    });
                     return;
                 }
                var e = new bsm({multiAllocationController: this, modal: BMT.modal});
                BMT.modal.show(e);
            },
             save: function() {
                _.each(this.$regions_dict, function(value, key){
                    this[key + "View"].save();
                }.bind(this));
                this.options.parent.block();
                this.model.save().fail(function(){ this.options.parent.unblock();}.bind(this)).then(function(){
                    this.options.parent.unblock();
                    var portfolio_key =  "goal_" + this.model.get("id") + "_" + this.model.get("portfolioSetId");
                    pss.deletePortfolioSet(portfolio_key);
                    pss.loadPortfolioSetForAccount(this.model).then(function(){this.options.parent.reRender()}.bind(this));
                }.bind(this));
            },
        })
    }), define("views/advice/adviceView", ["jquery", "underscore", "common/betterment.views", "hbs!views/advice/advice", "hbs!views/advice/noTargetFlyover", "hbs!views/advice/targetFlyover", "components/common/scripts/constants/accountStatus", "services/accountService", "viewHelpers/accountViewHelpers", "views/common/tabHeaderView", "components/portfolio/scripts/views/targetPortfolioDonutView", "views/common/questionsView", "views/advice/batchSettingsController", "views/advice/allocationRecommendationView", "views/advice/autoTransactionRecommendationView", "views/advice/depositRecommendationView", "views/advice/termRecommendationView", "views/advice/planRetirementAgeView", "components/advice/scripts/adviceGraphView", "views/advice/marketPerformanceView", "models/notification", "models/v2/retirementPlan", "views/notifications/adviceRetirementIncomeView", "views/notifications/dismissibleFlyoverView", "views/advice/planStartSavingView", "views/advice/planHeaderView", "services/flyoverService", "components/common/scripts/modules/async", "views/advice/multiAllocationView"], function(e, t, n, r, i, s, o, u, a, f, l, c, h, p, d, v, m, g, y, b, w, E, S, x, T, N, C, k, mav) {
        return n.View.extend({
            template: r,
            id: "advice",
            regions: {
                planRegion: ".plan-region",
                headerRegion: ".header-region",
                allocationRegion: ".allocation-region",
                autoTransactionRegion: ".auto-transaction-region",
                oneTimeDepositRegion: ".one-time-deposit-region",
                termRegion: ".term-region",
                donutRegion: ".donut-region",
                multiAllocationRegion: ".multi-allocation-region",
                marketPerformanceRegion: ".market-performance-region",
                graphRegion: ".graph-region"
            },
            events: {
                "click .collapse-circle": "toggleRecommendations",
                "click .set-all": "saveSettings",
                "click .reset-all": "resetSettings"
            },
            onInitialize: function() {
                this.model = BMT.selectedAccount, this.listenTo(BMT.vent, "addGoal:saved", function() {
                    this.reRender()
                })
            },
            onRender: function() {
                this.$settingsRow = this.$(".settings-row"), C.closeFlyover()
            },
            reRender: function() {
                this.block(), C.closeFlyover(), this.model = BMT.selectedAccount, this.loadAccountAndRender().then(this.unblock.bind(this))
            },
            onShow: function() {
                BMT.analytics.track("PageVisited", {
                    Location: "Advice"
                }), this.preloadStart(), this.loadAccountAndRender().then(this.preloadComplete.bind(this))
            },
            onDestroy: function() {
                C.closeFlyover()
            },
            loadAccountAndRender: function() {
                var n = this,
                    r = a.preloadSelectedAccount().then(function(t) {
                        var r = e.Deferred();
                        return n.model.isInPlan() ? E.create({
                            financialProfile: BMT.user.getFinancialProfile(),
                            financialPlan: n.model.get("financialPlan")
                        }).then(function(e) {
                            r.resolve(t, e)
                        }) : r.resolve(t), r.promise()
                    });
                return r.then(function(e, n) {
                    this.model = e, this.retirementPlan = n, this.renderSubViews(), this.toggleSaveButtons(), this.model.getCurrentBalanceWithPending() === 0 && t.defer(this.showFlyover.bind(this))
                }.bind(this))
            },
            renderSubViews: function() {
                this.renderPlanHeader(), this.renderHeader(), this.addAdviceBoxes(), this.renderDonut(), this.renderMultiAllocationRegion(), this.renderMarketPerformance(), this.renderGraph()
            },
            renderPlanHeader: function() {
                this.model.isInPlan() ? (this.planRegion.show(new N({
                    retirementPlan: this.retirementPlan
                })), this.$el.addClass("in-plan")) : (this.planRegion.empty(), this.$el.removeClass("in-plan"))
            },
            renderHeader: function() {
                this.headerView = new f({
                    model: this.model
                }), this.listenTo(this.headerView, "changeAccount", this.reRender), this.listenTo(this.headerView, "targetChanged", this.onValueChange), this.listenTo(this.headerView, "deleteAccount", this.reRender), this.listenTo(this.headerView, "goalStatusClicked", this.goalStatusClicked), this.listenTo(this.headerView, "autoTransactionChanged", this.reRender), this.headerRegion.show(this.headerView)
            },
            renderDonut: function() {
                this.donutView = new l({
                    model: this.model
                }), this.donutRegion.show(this.donutView)
            },
            renderMultiAllocationRegion: function() {
                this.multiAllocationview = new mav({
                    model: this.model,
                    parent: this
                }), this.multiAllocationRegion.show(this.multiAllocationview)
            },
            renderMarketPerformance: function() {
                this.marketPerformanceView = new b, this.marketPerformanceRegion.show(this.marketPerformanceView)
            },
            renderGraph: function() {
                this.graphView = new y({
                    model: this.model,
                    age: BMT.user.getAge(),
                    termYears: this.model.remainingGoalTerm(),
                    totalCurrentBalance: BMT.accounts().totalCurrentBalance(),
                    defaultFeeRate: BMT.accountGroup.defaultFeeRate()
                }), this.listenTo(this.graphView, "projectionChanged", function(e) {
                    this.marketPerformanceView.update(e)
                }), this.graphRegion.show(this.graphView)
            },
            onValueChange: function(e) {
                t.extend(this.changes, e), this.notifyBoxes(this.changes)
            },
            showFlyover: function() {
                var e = this.retirementPlan,
                    t = this.model,
                    n;
                t.isIncome() ? n = new w({}, {
                    view: S
                }) : this.model.isInPlan() && e.getRecommendedSavingsContributionForAccount(t) > 0 ? n = new w({}, {
                    view: T,
                    retirementPlan: e,
                    account: t
                }) : !this.model.isInPlan() && !t.num("goalAmount") ? n = new w({}, {
                    view: x,
                    template: i
                }) : n = new w({}, {
                    view: x,
                    template: s
                }), C.showFlyover(n, {
                    beforeShow: function(e) {
                        this.listenTo(e, "show", function() {
                            var t = this.oneTimeDepositRegion.$el,
                                n = t.offset(),
                                r = e.$el.parent().offset();
                            e.$el.css({
                                left: n.left - r.left - 40,
                                top: n.top - r.top + t.outerHeight() - 90
                            })
                        })
                    }.bind(this)
                })
            },
            addAdviceBoxes: function() {
                this.adviceBoxes = [], this.changes = {}, this.addAdviceBox(this.allocationRegion, new p({
                    modelKey: "allocationChangeTransaction",
                    model: this.model,
                    termYears: this.model.remainingGoalTerm()
                }), "allocationView"), this.addAdviceBox(this.autoTransactionRegion, new d({
                    model: this.model
                }), "autoTransactionView"), this.addAdviceBox(this.oneTimeDepositRegion, new v({
                    modelKey: "depositTransaction",
                    model: this.model
                }), "oneTimeDepositView"), this.model.isInPlan() ? this.addAdviceBox(this.termRegion, new g({
                    modelKey: "term",
                    retirementAge: this.financialPlan().num("retirementAge")
                })) : this.addAdviceBox(this.termRegion, new m({
                    modelKey: "term",
                    model: this.model
                })), this.$settingsRow.addClass("no-animate"), this.autoToggleRecommendations()
            },
            addAdviceBox: function(e, t, n) {
                e.show(t), this.adviceBoxes.push(t), this.listenTo(t, "valueChanged", this.onValueChange), this.listenTo(t, "valueChanged valueReset", this.toggleSaveButtons), n && (this[n] = t)
            },
            notifyBoxes: function(e) {
                t.each(this.adviceBoxes, function(t) {
                    t.refreshAdvice(e)
                }), this.$settingsRow.removeClass("no-animate"), this.autoToggleRecommendations(), this.donutView.update(e.allocation), this.graphView.update(e)
            },
            autoToggleRecommendations: function() {
                if (this.userHidRecommendationsLast) return;
                var e = t.chain(this.adviceBoxes).filter(function(e) {
                    return e !== this.allocationView
                }, this).all(function(e) {
                    return !e.hasRecommendation()
                }).value();
                e ? (this.hideRecommendations(), this.$(".collapse-circle").addClass("hidden")) : (this.showRecommendations(), this.$(".collapse-circle").removeClass("hidden"))
            },
            toggleRecommendations: function() {
                this.$settingsRow.removeClass("no-animate"), this.$settingsRow.hasClass("short") ? (this.userHidRecommendationsLast = !1, this.showRecommendations()) : (this.userHidRecommendationsLast = !0, this.hideRecommendations())
            },
            showRecommendations: function() {
                this.$settingsRow.removeClass("short"), this.$settingsRow.find(".collapse-label").text("Hide Recommendations")
            },
            hideRecommendations: function() {
                this.$settingsRow.addClass("short"), this.$settingsRow.find(".collapse-label").text("Show Recommendations")
            },
            goalStatusClicked: function(e) {
                e === o.OFF_TRACK && (this.showRecommendations(), this.showFlyover())
            },
            saveSettings: function() {
                if (!this.isAnythingDirty()) return;
                if (this.autoTransactionView.validate()) return;
                var e = {
                    account: this.model,
                    onSuccess: function() {
                        this.reRender()
                    }.bind(this)
                };
                t.extend(e, this.getModelsForSave()), h.go(e)
            },
            resetSettings: function() {
                if (!this.isAnythingDirty()) return;
                t.each(this.adviceBoxes, function(e) {
                    e.reset()
                })
            },
            toggleSaveButtons: function() {
                this.$(".save-buttons").toggle(this.isAnythingDirty());
                var e = "Set",
                    t = "Reset";
                this.numberOfDirtySettings() > 1 && (e = "Set All", t = "Reset All"), this.$(".save-buttons .set-all").text(e), this.$(".save-buttons .reset-all").text(t)
            },
            getModelsForSave: function() {
                return t.reduce(this.adviceBoxes, function(e, n) {
                    return t.extend(e, n.getModelForSave())
                }, {})
            },
            isAnythingDirty: function() {
                return t.any(this.adviceBoxes, function(e) {
                    return e.isDirty()
                })
            },
            numberOfDirtySettings: function() {
                return t.filter(this.adviceBoxes, function(e) {
                    return e.isDirty()
                }).length
            },
            financialPlan: function() {
                return BMT.user.get("financialPlans").selected()
            }
        })
    });