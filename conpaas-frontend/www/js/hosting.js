/*
 * Copyright (c) 2010-2012, Contrail consortium.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms,
 * with or without modification, are permitted provided
 * that the following conditions are met:
 *
 *  1. Redistributions of source code must retain the
 *     above copyright notice, this list of conditions
 *     and the following disclaimer.
 *  2. Redistributions in binary form must reproduce
 *     the above copyright notice, this list of
 *     conditions and the following disclaimer in the
 *     documentation and/or other materials provided
 *     with the distribution.
 *  3. Neither the name of the Contrail consortium nor the
 *     names of its contributors may be used to endorse
 *     or promote products derived from this software
 *     without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
 * CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * @require conpaas.js, servicepage.js
 */
conpaas.ui = (function (this_module) {
    /**
     * conpaas.ui.HostingPage
     */
    this_module.HostingPage = conpaas.new_constructor(
    /* extends */conpaas.ui.ServicePage,
    /* constructor */function (server, service) {
        this.server = server;
        this.service = service;
        this.setupPoller_();
    },
    /* methods */{
    /**
     * @override conpaas.ui.ServicePage.freezeInput
     */
    freezeInput: function (freeze) {
        var linksSelector = '.versions .activate';
        conpaas.ui.ServicePage.prototype.freezeInput.call(this, freeze);
        if (freeze) {
            $(linksSelector).hide();
        } else {
            $(linksSelector).show();
        }
    },
    /**
     * @override conpaas.ui.ServicePage.attachHandlers
     */
    attachHandlers: function () {
        var that = this;
        conpaas.ui.ServicePage.prototype.attachHandlers.call(this);
        // this is the goofy ajax file submit form provided by a jQuery plugin
        $('#fileForm').ajaxForm({
            dataType: 'json',
            success: function (response) {
                $('.additional .loading').toggleClass('invisible');
                $('#file').val('');
                $('.additional .positive').show();
                setTimeout(function () {
                    $('.additional .positive').fadeOut();
                }, 1000);
                that.reloadVersions();
            },
            error: function (response) {
                that.poller.stop();
                // show the error
                that.server.handleError({name: 'service error',
                    details: response.error});
           }
        });
        $('#fileForm input:file').change(function() {
            $('.additional .loading').toggleClass('invisible');
            $('#fileForm').submit();
        });
        $('.versions .activate').click(that, that.onActivateVersion);
        $('.deployoption input[type=radio]').change(function() {
            $('.deployactions').toggleClass('invisible');
        });
        // configuration handlers
        $('#conf-maxexec, #conf-memlim').change(function() {
            $('#saveconf').removeAttr('disabled');
        });
        $('#saveconf').click(that, that.onSaveConfig);
    },
    // handlers
    onActivateVersion: function (event) {
        var page = event.data,
            versionId = $(event.target).attr('name');
        $('.versions .activate').hide();
        $(event.target).parent().find('.loading').show();
        page.freezeInput(true);
        page.updateConfiguration({codeVersionId: versionId}, function () {
            page.displayInfo('updating all the instances...');
            page.pollState(function () {
                window.location.reload();
            });
        }, function () {
            page.freezeInput(false);
        });
    },
    onSaveConfig: function (event) {
        var page = event.data,
            params = {phpconf: {
                max_execution_time: $('#conf-maxexec').val(),
                memory_limit: $('#conf-memlim').val()
            }};
        $(event.target).attr('disabled', 'disabled');
        page.updateConfiguration(params, function () {
            $('.settings-form .actions .positive').show();
            setTimeout(function () {
                $('.settings-form .actions .positive').fadeOut();
            }, 2000);
        }, function () {
            $(event.target).removeAttr('disabled');
        });
    },
    /**
     * load the rendered HTML for the versions container
     */
    reloadVersions: function () {
        var that = this;
        this.server.reqHTML('ajax/render.php',
                {sid: this.service.sid, target: 'versions'}, 'get',
                function (response) {
                    $('#versionsWrapper').html(response);
                    $('.versions .activate').click(that,
                            that.onActivateVersion);
                });
    }
    });

    return this_module;
}(conpaas.ui || {}));

$(document).ready(function () {
    var service,
        page,
        sid = GET_PARAMS['sid'],
        server = new conpaas.http.Xhr();
    server.req('ajax/getService.php', {sid: sid}, 'get', function (data) {
        service = new conpaas.model.Service(data.sid, data.state,
                data.instanceRoles, data.reachable);
        page = new conpaas.ui.HostingPage(server, service);
        page.attachHandlers();
        if (page.service.needsPolling()) {
            page.freezeInput(true);
            page.pollState(function () {
                window.location.reload();
            });
        }
    }, function () {
        // error
        window.location = 'index.php';
    })
});