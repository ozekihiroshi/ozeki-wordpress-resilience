/* Native media queues wait asynchronously for the existing S3-first worker. */
(() => {
    if(!window.wp||!wp.Uploader)return;
    const init=wp.Uploader.prototype.init;
    wp.Uploader.prototype.init=function(){
        const uploader=this.uploader;
        uploader.bind('BeforeUpload',()=>{uploader.settings.multipart_params._owr_parent=window.owrNative.parent;});
        uploader.bind('FileUploaded',(up,file,response)=>{
            let value;
            try{value=JSON.parse(response.response);}catch(e){return;}
            if(!value.success||!value.data.owr_pending){
                if(value.success&&value.data.owr_parent)window.owrNative.parent=value.data.owr_parent;
                return;
            }
            up.stop();
            const request=value.data;
            (async()=>{
                try {
                    for(let i=0;i<180;i++){
                        const state=await wp.apiFetch({path:'/owr-materials/v1/state'});
                        if(state.pending?.operation!==request.operation)throw new Error('保存要求が変わりました。S3先行編集で状態を確認してください。');
                        if(['failed','blocked'].includes(state.state))throw new Error('S3保存が停止しました。S3先行編集から同じ要求を再開してください。');
                        if(state.state==='stored'){
                            await wp.apiFetch({path:'/owr-materials/v1/apply',method:'POST'});
                            const result=await wp.apiFetch({path:'/owr-materials/v1/native-result?asset='+encodeURIComponent(request.asset)});
                            if(!result.attachment?.id)throw new Error('画像の反映結果を確認できません。');
                            result.attachment.owr_parent=result.parent;
                            up.trigger('FileUploaded',file,{response:JSON.stringify({success:true,data:result.attachment})});
                            up.start();
                            return;
                        }
                        await new Promise(resolve=>setTimeout(resolve,1000));
                    }
                    throw new Error('S3保存は継続中です。S3先行編集で状態を確認してください。再アップロードは不要です。');
                }catch(e){
                    up.trigger('FileUploaded',file,{response:JSON.stringify({success:false,data:{message:e.message||'保存状態を確認してください。'}})});
                }
            })();
            // Suppress the standard success callback until an actual attachment exists.
            return false;
        },null,100);
        return init.apply(this,arguments);
    };
})();
