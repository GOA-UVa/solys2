function status=Intra_cfg(cmd,com)
global INTRA PSR

status=-1;

if nargin<2,com=[];end
if isempty(com),com=INTRA.COMport;else INTRA.COMport=com;end

switch cmd
    case 'o'
        if sum(strcmpi({'KIPP','SOLYS','KIPP_SOLYS','KIPP_AP'},INTRA.TRACKER_BRAND))==0
            a=instrfindall('type','serial','port',com);
%             while  isempty(a)
%                 com=inputdlg([com  ' N/A: Enter a valid  COM port '],'COMPort',1,{'COMx'});
%                 com=char(com);
%                 a=instrfindall('type','serial','port',com);
%             end
            try fclose(a);delete(a);end
            try
                INTRA.COM=serial(com);
                if INTRA.ver>=2
                    set(INTRA.COM,'Terminator','CR','BaudRate',57600);
                else
                    set(INTRA.COM,'Terminator','CR','BaudRate',9600,'Timeout',5);
                end
                
                fopen(INTRA.COM);
                status=strcmpi(INTRA.COM.Status,'open');
               
            end
        else
            if  any(strfind(INTRA.TRACKER_BRAND,'_AP'))
                a=instrfindall('type','serial','port',com);
%                 while  isempty(a)
%                     com=inputdlg([com  ' N/A: Enter a valid  COM port '],'COMPort',1,{'COMx'});
%                     com=char(com);
%                     a=instrfindall('type','serial','port',com);
%                 end
                try fclose(a);delete(a);end
                INTRA.COM=serial(com);
                set(INTRA.COM,'Terminator','CR','BaudRate',9600,'Timeout',5);
                INTRA.Password='PW 792';
                INTRA.Password='PW 65535';
            else
                com=mac2IP;com=unique(com);
                a=instrfindall('type','tcpip','RemoteHost',com{:}); 
                try fclose(a);delete(a);end
                INTRA.COM=tcpip(com{:},15000);
                INTRA.COMport=com{:};
                INTRA.Password='PW 65535';
            end
            set(INTRA.COM,'Terminator','CR','Timeout',5);
            fopen(INTRA.COM);
            
            status=strcmpi(INTRA.COM.Status,'open'); 
             Kipp_cmd('init');
           
        end
    case 'c'
        try fclose(INTRA.COM);disp(INTRA.COM);end
        disp([datestr(now) '   INTRA COM/IP ' INTRA.COMport ' free']);
        try,INTRA=rmfield(INTRA,'COM');end
        a=instrfindall('type','serial','port',INTRA.COMport);
        try fclose(a);delete(a);end
        try
        a=instrfindall('type','tcpip','RemoteHost',INTRA.COMport);
        try fclose(a);delete(a);end
        end
        status=1;
        return;
    case 're'
       try, Intra_cfg('c',com);pause(10);end
        status=Intra_cfg('o',com);
        
end
try
    PSR.TRACKER.COM=INTRA.COM;
end