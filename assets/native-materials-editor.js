/* Native Gutenberg saves use the existing durable S3-first worker. */
(() => {
    let busy = false;
    const api = wp.apiFetch;
    const notice = (message, type='info') => wp.data.dispatch('core/notices').createNotice(type, message, {id:'owr-save',isDismissible:true});
    api.use(async (options, next) => {
        const path = options.path || '';
        if (!/^\/wp\/v2\/(posts|pages|media)(\/\d+)?(\?|$)/.test(path) || !['POST','PUT','PATCH'].includes((options.method||'GET').toUpperCase())) return next(options);
        if (busy) throw {message:'S3への保存処理中です。完了後に再操作してください。',code:'owr_busy'};
        busy=true;
        try {
            notice('S3へ原本を保存しています。確定前は公開内容を変更しません。');
            let result=await next({...options,headers:{...options.headers,'X-OWR-Parent':window.owrNative.parent}});
            if(!result.owr_pending)throw {message:'S3保存応答を確認できません。'};
            const asset=result.asset, operation=result.pending.operation;
            for(let i=0;i<180;i++) {
                if(result.pending && result.pending.operation!==operation)throw {message:'別の保存要求です。画面を更新してください。'};
                if(result.state==='stored') {
                    await api({path:'/owr-materials/v1/apply',method:'POST'});
                    const state=await api({path:'/owr-materials/v1/native-result?asset='+encodeURIComponent(asset)});
                    window.owrNative.parent=state.parent;
                    notice('S3保存が確定し、WordPressへ反映しました。','success');
                    return api({path:'/wp/v2/'+state.route+'/'+state.id+'?context=edit'});
                }
                if(['failed','blocked'].includes(result.state))throw {message:'S3保存が停止しました。公開内容は保持されています。「S3先行編集」で同じ要求を再開してください。'};
                await new Promise(resolve=>setTimeout(resolve,1000));result=await api({path:'/owr-materials/v1/state'});
            }
            throw {message:'保存処理は継続中です。「S3先行編集」で状態を確認・再開できます。'};
        } catch(error) { notice(error.message||'保存を停止しました。','error');throw error; }
        finally {busy=false;}
    });
})();
