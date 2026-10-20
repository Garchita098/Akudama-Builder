package com.akudama.studio;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.content.res.ColorStateList;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.*;
import org.json.*;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private static final String REPO = "Garchita098/Akudama-Builder";
    private static final String WEB = "https://github.com/" + REPO;
    private final int bg=0xff0b111d, panel=0xff1b2a3e, blue=0xff8bccff, muted=0xffa4b5c9, green=0xff7de0b0, red=0xffff8f96;
    private LinearLayout body;
    private String page="Обзор";
    private String accessToken="";
    private JSONArray lastRuns=null;
    private boolean loading=false;

    int dp(int v){return (int)(getResources().getDisplayMetrics().density*v+.5f);}
    TextView text(String s,int size,int color){
        TextView t=new TextView(this);t.setText(s);t.setTextColor(color);t.setTextSize(size);return t;
    }
    GradientDrawable round(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}
    void space(int height){View v=new View(this);body.addView(v,new LinearLayout.LayoutParams(1,dp(height)));}
    void card(String heading,String detail){
        LinearLayout pane=new LinearLayout(this);pane.setOrientation(LinearLayout.VERTICAL);
        pane.setPadding(dp(17),dp(15),dp(17),dp(15));pane.setBackground(round(panel,16));
        TextView h=text(heading,17,Color.WHITE);h.setTypeface(null,Typeface.BOLD);pane.addView(h);
        if(!detail.isEmpty()){TextView sub=text(detail,14,muted);sub.setPadding(0,dp(6),0,0);pane.addView(sub);}
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(11);body.addView(pane,lp);
    }
    void button(String title,Runnable action){
        TextView b=text(title,15,bg);b.setTypeface(null,Typeface.BOLD);
        b.setGravity(Gravity.CENTER);b.setBackground(round(blue,12));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,dp(50));lp.bottomMargin=dp(10);
        body.addView(b,lp);b.setOnClickListener(v->action.run());
    }
    void open(String url){startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(url)));}
    void tab(LinearLayout row,String name){
        TextView b=text(name,12,page.equals(name)?blue:muted);
        b.setGravity(Gravity.CENTER);b.setBackground(round(page.equals(name)?panel:bg,12));
        row.addView(b,new LinearLayout.LayoutParams(0,dp(54),1));
        b.setOnClickListener(v->show(name));
    }
    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        getWindow().setStatusBarColor(bg);getWindow().setNavigationBarColor(bg);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        show("Обзор");
    }
    void show(String selected){
        page=selected;
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
        root.setFitsSystemWindows(true);root.setBackgroundColor(bg);
        root.setPadding(dp(18),dp(12),dp(18),dp(8));
        TextView brand=text("AKUDAMA   /   STUDIO",20,Color.WHITE);
        brand.setTypeface(null,Typeface.BOLD);brand.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(brand,new LinearLayout.LayoutParams(-1,dp(52)));
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);
        body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(0,dp(16),0,dp(24));scroll.addView(body);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        TextView section=text(page,26,Color.WHITE);section.setTypeface(null,Typeface.BOLD);body.addView(section);space(18);
        switch(page){
          case "Обзор":
            card("Центр разработки","Сборка APK, Android-эмулятор и тесты через GitHub Actions.");
            card("Проект: Akudama Studio","Нативное Android-приложение · версия 0.2");
            button("ПОСМОТРЕТЬ СБОРКИ",()->show("Сборки"));
            button("ОТКРЫТЬ GITHUB",()->open(WEB));
            break;
          case "Проекты":
            card("Akudama Studio","projects/studio · приложение центра сборок");
            card("Legacy Test","project.zip · тестовое приложение");
            button("ОТКРЫТЬ ФАЙЛЫ ПРОЕКТОВ",()->open(WEB+"/tree/main/projects"));
            break;
          case "Сборки":
            card("Реальные сборки GitHub Actions",accessToken.isEmpty()?
                "Для приватного репозитория требуется токен с правом Actions: Read. Токен хранится только в памяти приложения.":
                "Авторизовано на текущий сеанс. Можно обновлять список запусков.");
            if(accessToken.isEmpty()){button("ПОДКЛЮЧИТЬ GITHUB",()->promptToken());}
            else {
                button(loading?"ЗАГРУЗКА...":"ОБНОВИТЬ СБОРКИ",()->fetchRuns());
                button("ОТКЛЮЧИТЬ АККАУНТ",()->{accessToken="";lastRuns=null;show("Сборки");});
                if(lastRuns!=null)renderRuns();
            }
            button("ОТКРЫТЬ ACTIONS В БРАУЗЕРЕ",()->open(WEB+"/actions"));
            break;
          default:
            card("Диагностика","После каждого теста GitHub хранит скриншоты и logcat в Android-Emulator-Diagnostics.");
            button("ОТКРЫТЬ ОТЧЁТЫ",()->open(WEB+"/actions"));
            card("Безопасность","Секреты не встроены в APK. GitHub-токен удаляется из памяти при завершении процесса.");
        }
        LinearLayout nav=new LinearLayout(this);nav.setBackground(round(panel,14));
        tab(nav,"Обзор");tab(nav,"Проекты");tab(nav,"Сборки");tab(nav,"Отчёты");
        root.addView(nav,new LinearLayout.LayoutParams(-1,dp(60)));
        setContentView(root);
    }
    void promptToken(){
        EditText input=new EditText(this);
        input.setSingleLine(true);input.setHint("github_pat_...");
        input.setInputType( android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        LinearLayout wrap=new LinearLayout(this);wrap.setPadding(dp(16),0,dp(16),0);wrap.addView(input);
        new android.app.AlertDialog.Builder(this).setTitle("GitHub: read-only доступ")
        .setMessage("Создай fine-grained personal access token для Akudama-Builder с разрешением Actions: Read. Не используй токен с правом записи.")
        .setView(wrap).setNegativeButton("Отмена",null)
        .setPositiveButton("Подключить",(d,w)->{
            accessToken=input.getText().toString().trim();
            if(accessToken.length()<15){accessToken="";Toast.makeText(this,"Токен не указан",Toast.LENGTH_SHORT).show();return;}
            fetchRuns();
        }).show();
    }
    void fetchRuns(){
        if(loading || accessToken.isEmpty())return;
        loading=true;show("Сборки");
        final String token=accessToken;
        new Thread(()->{
            String failure=null;JSONArray runs=null;
            HttpURLConnection connection=null;
            try {
                URL url=new URL("https://api.github.com/repos/"+REPO+"/actions/runs?per_page=12");
                connection=(HttpURLConnection)url.openConnection();
                connection.setRequestProperty("Authorization","Bearer "+token);
                connection.setRequestProperty("Accept","application/vnd.github+json");
                connection.setRequestProperty("X-GitHub-Api-Version","2022-11-28");
                connection.setConnectTimeout(12000);connection.setReadTimeout(12000);
                int status=connection.getResponseCode();
                if(status!=200)throw new IOException("GitHub HTTP "+status);
                ByteArrayOutputStream buffer=new ByteArrayOutputStream();
                try(InputStream stream=connection.getInputStream()){
                  byte[] bytes=new byte[4096];int n;
                  while((n=stream.read(bytes))!=-1)buffer.write(bytes,0,n);
                }
                runs=new JSONObject(buffer.toString("UTF-8")).getJSONArray("workflow_runs");
            }catch(Exception e){failure=e.getMessage();}
            finally{if(connection!=null)connection.disconnect();}
            final JSONArray result=runs;final String error=failure;
            runOnUiThread(()->{
                loading=false;
                if(!token.equals(accessToken))return;
                if(error!=null)Toast.makeText(this,"Ошибка загрузки: "+error,Toast.LENGTH_LONG).show();
                else lastRuns=result;
                if(page.equals("Сборки"))show("Сборки");
            });
        }).start();
    }
    void renderRuns(){
        if(lastRuns.length()==0){card("Сборок пока нет","GitHub не вернул запусков");return;}
        for(int i=0;i<Math.min(12,lastRuns.length());i++){
            JSONObject r=lastRuns.optJSONObject(i);if(r==null)continue;
            String state=r.optString("conclusion");
            if(state.equals("null")||state.isEmpty())state=r.optString("status","unknown");
            final String link=r.optString("html_url",WEB+"/actions");
            String title="#"+r.optInt("run_number")+" · "+state;
            card(title,r.optString("display_title","Build")+"\n"+r.optString("created_at",""));
            button("ОТКРЫТЬ #"+r.optInt("run_number"),()->open(link));
        }
    }
}
