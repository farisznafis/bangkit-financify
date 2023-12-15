package com.code.precapstone.view.main

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.code.precapstone.R
import com.code.precapstone.data.model.ListNews
import com.code.precapstone.databinding.ActivityMainBinding
import com.code.precapstone.view.adapter.news.NewsAdapter
import com.code.precapstone.view.category.CategoryActivity
import com.code.precapstone.view.setting.SettingsActivity

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        //menampilkan berita
        val rv = binding.rvNews
        val newsAdapter = NewsAdapter(ListNews().dummyListNews)
        rv.adapter = newsAdapter
        rv.layoutManager = LinearLayoutManager(this)


        //berpindah ke setting activity
        binding.ivSetting.setOnClickListener{
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }

        //berpindah ke categotu activity
        binding.fab.setOnClickListener{
            val intent = Intent(this, CategoryActivity::class.java)
            startActivity(intent)
        }

    }
}