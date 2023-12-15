package com.code.precapstone.view.articles

import android.annotation.SuppressLint
import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.webkit.WebView
import com.code.precapstone.R
import com.code.precapstone.databinding.ActivityArticlesBinding
import com.code.precapstone.view.main.MainActivity

class ArticlesActivity : AppCompatActivity() {

    private lateinit var binding: ActivityArticlesBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityArticlesBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val webView: WebView = findViewById(R.id.wvNews)
        val url = intent.getStringExtra("url")

        binding.tvBack.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
            finish()
        }

        @SuppressLint("SetJavaScriptEnabled")
        webView.settings.javaScriptEnabled = true
        if (url != null) {
            webView.loadUrl(url)
        }

    }
}