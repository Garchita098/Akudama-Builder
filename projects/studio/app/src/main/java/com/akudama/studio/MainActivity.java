package com.akudama.studio;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.content.res.ColorStateList;
import android.view.View;
import android.widget.*;
public class MainActivity extends Activity {
 final int bg=0xff0b111d, panel=0xff1b2a3e, blue=0xff8bccff;
 LinearLayout body;
 int dp(int x){return (int)(getResources().getDisplayMetrics().density*x+.5f);}
 TextView text(String s,int size){TextView t=new TextView(this);t.setText(s);t.setTextColor(-1);t.setTextSize(size);return t;}
 void gap(){View v=new View(this);body.addView(v,new LinearLayout.LayoutParams(1,dp(14)));}
 void card(String title,String detail){
 LinearLayout box=new LinearLayout(this);box.setOrientation(1);box.setPadding(dp(18),dp(16),dp(18),dp(16));
 GradientDrawable d=new GradientDrawable();d.setColor(panel);d.setCornerRadius(dp(14));box.setBackground(d);
 TextView h=text(title,20);h.setTypeface(null,Typeface.BOLD);box.addView(h);
 TextView sub=text(detail,14);sub.setTextColor(blue);box.addView(sub);
 LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(10);body.addView(box,p);
 }
 void link(String label,String url){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setTextColor(bg);b.setBackgroundTintList(ColorStateList.valueOf(blue));b.setOnClickListener(v->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(url))));body.addView(b,new LinearLayout.LayoutParams(-1,dp(52)));}
 void tab(LinearLayout row,String name){Button b=new Button(this);b.setText(name);b.setTextSize(11);b.setAllCaps(false);b.setTextColor(blue);b.setOnClickListener(v->show(name));row.addView(b,new LinearLayout.LayoutParams(0,dp(54),1));}
 @Override public void onCreate(Bundle b){super.onCreate(b);getWindow().setStatusBarColor(bg);getWindow().setNavigationBarColor(bg);show("Обзор");}
 void show(String page){
 LinearLayout root=new LinearLayout(this);root.setOrientation(1);root.setPadding(dp(12),dp(8),dp(12),dp(8));root.setBackgroundColor(bg);
 TextView header=text("AKUDAMA STUDIO",24);header.setTypeface(null,Typeface.BOLD);root.addView(header,new LinearLayout.LayoutParams(-1,dp(65)));
 ScrollView scroll=new ScrollView(this);body=new LinearLayout(this);body.setPadding(dp(3),dp(16),dp(3),dp(16));body.setOrientation(1);scroll.addView(body);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
 TextView section=text(page,23);body.addView(section);gap();
 String url="https://github.com/Garchita098/Akudama-Builder";
 if(page.equals("Обзор")){card("AKUDAMA BUILDER","Центр управления Android-проектами");card("Сборка и тесты","GitHub Actions собирает APK и проверяет его в эмуляторе");link("ОТКРЫТЬ СБОРКИ",url+"/actions");}
 else if(page.equals("Проекты")){card("Akudama Studio","Мобильный центр разработки · версия 0.1");card("Legacy Test","Наше первое тестовое приложение");link("ОТКРЫТЬ ПРОЕКТЫ",url+"/tree/main/projects");}
 else if(page.equals("Сборки")){card("Последние сборки","Список доступен в GitHub Actions");link("ОТКРЫТЬ ACTIONS",url+"/actions");}
 else {card("Отчёты","Скриншоты и логи Android-эмулятора доступны в артефактах каждой сборки");card("Безопасность","Токен GitHub не хранится в APK");link("ПОСМОТРЕТЬ ОТЧЁТЫ",url+"/actions");}
 LinearLayout bar=new LinearLayout(this);tab(bar,"Обзор");tab(bar,"Проекты");tab(bar,"Сборки");tab(bar,"Отчёты");root.addView(bar);
 setContentView(root);
 }
}